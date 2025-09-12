import os
import json
import asyncio
import tempfile
import unittest
from typing import Optional

from unittest.mock import patch

import receive as receive_mod
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from database.db import Base
from models.models import PredictionSession, DetectionObject


class FakeMessage:
    def __init__(self, body: bytes) -> None:
        self.body = body
        self.acked = False
        self.requeued: Optional[bool] = None

    def process(self, requeue: bool = False):
        outer = self

        class _CM:
            async def __aenter__(self):
                return None

            async def __aexit__(self, exc_type, exc, tb):
                outer.acked = True
                outer.requeued = requeue
                return False

        return _CM()


def _write_bytes(path: str, content: bytes) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(content)


class TestReceiveWorker(unittest.TestCase):
    @patch("receive.predictor")
    @patch("receive.download_s3_key_to_path")
    def test_handle_message_s3_success(self, mock_download, mock_predictor):

        # Prepare predictor and s3 mocks
        def fake_download(key: str, dest_path: str) -> None:
            _write_bytes(dest_path, b"fake-jpeg-bytes")

        mock_download.side_effect = fake_download

        def fake_predict(original_path: str, predicted_path: str):
            _write_bytes(predicted_path, b"fake-predicted-jpeg-bytes")
            return [
                {"label": "person", "score": 0.9, "box": [0, 0, 10, 10]},
                {"label": "car", "score": 0.8, "box": [5, 5, 20, 20]},
            ], 2

        mock_predictor.predict_to_file.side_effect = fake_predict

        # Temp workspace (dirs + sqlite file)
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_worker.db")
            engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})

            # Ensure models are registered (receive imports queries -> models), then create tables
            Base.metadata.create_all(bind=engine)
            SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

            uploads_dir = os.path.join(tmpdir, "uploads")
            original_dir = os.path.join(uploads_dir, "original")
            predicted_dir = os.path.join(uploads_dir, "predicted")
            chats_dir = os.path.join(uploads_dir, "chats")

            # Per-test overrides for worker module state
            with patch.object(receive_mod, "SessionLocal", SessionLocal, create=True), \
                 patch.object(receive_mod, "UPLOAD_DIR", original_dir, create=True), \
                 patch.object(receive_mod, "PREDICTED_DIR", predicted_dir, create=True), \
                 patch.object(receive_mod, "CHATS_BASE_DIR", chats_dir, create=True):

                payload = {
                    "type": "yolo_predict",
                    "img": "predicted/beatles.jpg",
                    "chat_id": "chat-123",
                    "callback_url": None,
                    "prediction_uid": "unit-test-uid-1",
                    "user_id": 42,
                }
                message = FakeMessage(json.dumps(payload).encode("utf-8"))

                asyncio.run(receive_mod.handle_message(message))

                self.assertTrue(message.acked)

                # Query DB and assert rows/files
                session: Session = SessionLocal()
                try:
                    ps = (
                        session.query(PredictionSession)
                        .filter_by(uid="unit-test-uid-1", user_id=42)
                        .first()
                    )
                    self.assertIsNotNone(ps)
                    self.assertTrue(os.path.exists(ps.original_image))
                    self.assertTrue(os.path.exists(ps.predicted_image))

                    dets = session.query(DetectionObject).filter_by(prediction_uid="unit-test-uid-1").all()
                    self.assertEqual(len(dets), 2)
                    self.assertCountEqual([d.label for d in dets], ["person", "car"])
                finally:
                    session.close()



if __name__ == "__main__":
    unittest.main()


