import asyncio
import json
import os
import tempfile
import uuid
from typing import Any, Dict, Optional

import aio_pika
import httpx

from database.db import SessionLocal
from queries.queries import save_detection_object, save_prediction_session
from services.predictor import YoloPredictor
from services.s3 import download_s3_key_to_path
from services.event_publisher import publish_event
from dependencies.auth import ensure_anonymous_user
from models.models import User


RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost/")
QUEUE_NAME = os.getenv("PREDICT_QUEUE", "yolo.predict")
CALLBACK_URL = os.getenv("CALLBACK_URL")  # default; can be overridden per message


UPLOAD_DIR = "uploads/original"
PREDICTED_DIR = "uploads/predicted"
CHATS_BASE_DIR = "uploads/chats"


os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(PREDICTED_DIR, exist_ok=True)


predictor = YoloPredictor()


async def _send_callback(payload: Dict[str, Any], callback_url_override: Optional[str] = None) -> None:
    target_url = callback_url_override or CALLBACK_URL
    if not target_url:
        # Fallback to logging when callback is not configured
        print("[callback-disabled]", json.dumps(payload))
        return
    timeout = httpx.Timeout(10.0, connect=5.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            await client.post(target_url, json=payload)
        except Exception as exc:
            print(f"Failed to send callback: {exc}")


def _persist_input_file_from_payload(payload: Dict[str, Any], uid: str) -> str:
    """Persist/resolve input image locally from the given payload.

    Supported payloads (from OllamaUI):
    - { "img": "<s3_key>", ... }
    - { "source": "path", "path": "/abs/or/relative/path.jpg" }
    """
    # Case 1: S3 key via 'img'
    if "img" in payload and payload["img"]:
        s3_key = str(payload["img"]).lstrip("/")
        base_name = os.path.basename(s3_key)
        name, ext = os.path.splitext(base_name)
        if not ext:
            ext = ".jpg"
        final_filename = f"{name}-{uid}{ext}"
        original_path = os.path.join(UPLOAD_DIR, final_filename)
        download_s3_key_to_path(s3_key, original_path)
        return original_path

    # Case 2: explicit local path
    source = payload.get("source")
    if source == "path" and "path" in payload:
        return str(payload["path"])

    raise ValueError("Unsupported payload. Provide 'img' (S3 key) or {'source':'path','path':...}.")


async def handle_message(message: aio_pika.IncomingMessage) -> None:
    async with message.process(requeue=False):
        data = json.loads(message.body.decode("utf-8"))

        raw_user_id = data.get("user_id")
        chat_id: Optional[str] = data.get("chat_id")
        username: Optional[str] = data.get("username")
        callback_url_override: Optional[str] = data.get("callback_url")
        # Use incoming prediction UID if supplied; else generate
        uid = str(data.get("prediction_uid")) if data.get("prediction_uid") else str(uuid.uuid4())
        print(f" [>] Received job uid={uid} chat_id={chat_id}")
        try:
            original_path = _persist_input_file_from_payload(data, uid)
        except Exception as exc:
            print(f"Invalid job payload: {exc}")
            return

        # Build predicted path (optionally per chat)
        if chat_id:
            predicted_dir = os.path.join(CHATS_BASE_DIR, chat_id, "predicted")
        else:
            predicted_dir = PREDICTED_DIR
        os.makedirs(predicted_dir, exist_ok=True)
        predicted_path = os.path.join(
            predicted_dir, f"{os.path.splitext(os.path.basename(original_path))[0]}-{uid}.jpg"
        )

        detections, count = predictor.predict_to_file(original_path, predicted_path)

        # Persist DB rows
        db = SessionLocal()
        try:
            # Resolve effective user id: explicit user_id -> username -> anonymous
            if raw_user_id is not None:
                effective_user_id = int(raw_user_id)
            elif username:
                user = db.query(User).filter_by(username=username).first()
                if not user:
                    user = User(username=username, password="__none__")
                    db.add(user)
                    db.commit()
                    db.refresh(user)
                effective_user_id = user.id
            else:
                effective_user_id = ensure_anonymous_user(db)

            save_prediction_session(
                db=db,
                uid=uid,
                original_image=original_path,
                predicted_image=predicted_path,
                user_id=effective_user_id,
            )
            for det in detections:
                save_detection_object(
                    db=db,
                    prediction_uid=uid,
                    label=det["label"],
                    score=float(det["score"]),
                    box=str(det["box"]),
                )
        finally:
            db.close()

        # Send callback/log
        await _send_callback(
            {
                "prediction_uid": uid,
                "user_id": effective_user_id,
                "labels": [d["label"] for d in detections],
                "detection_count": count,
                "predicted_path": predicted_path,
            }
        , callback_url_override)

        # Publish domain event for other microservices
        try:
            await publish_event(
                routing_key="images.processed",
                payload={
                    "prediction_uid": uid,
                    "user_id": effective_user_id,
                    "labels": [d["label"] for d in detections],
                    "detection_count": count,
                    "chat_id": chat_id,
                },
            )
        except Exception as exc:
            print(f"[events] publish failed: {exc}")


async def main() -> None:
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    queue_name = QUEUE_NAME
    async with connection:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=1)
        queue = await channel.declare_queue(queue_name, durable=True)
        print(f" [*] Waiting for messages in '{queue_name}'. To exit press CTRL+C")
        await queue.consume(handle_message)
        await asyncio.Future()


if __name__ == "__main__":  # pragma: no cover
    asyncio.run(main())


