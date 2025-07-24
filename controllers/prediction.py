import os
import shutil
import time
import uuid
from fastapi import APIRouter, Depends
from fastapi import UploadFile, File, HTTPException
from sqlalchemy.orm import Session
import torch
from ultralytics import YOLO
from PIL import Image

from database.db import get_db
from dependencies.auth import get_current_user_id
from queries.queries import save_detection_object, save_prediction_session

router = APIRouter()

UPLOAD_DIR = "uploads/original"
PREDICTED_DIR = "uploads/predicted"
DB_PATH = "predictions.db"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(PREDICTED_DIR, exist_ok=True)
torch.cuda.is_available = lambda: False

# Download the AI model (tiny model ~6MB)
model = YOLO("yolov8n.pt")



@router.post("/predict")
def predict(
    user_id: int = Depends(get_current_user_id),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Predict objects in an image and save results to database
    """
    start_time = time.time()

    # Generate file paths
    ext = os.path.splitext(file.filename)[1]
    uid = str(uuid.uuid4())
    original_path = os.path.join(UPLOAD_DIR, uid + ext)
    predicted_path = os.path.join(PREDICTED_DIR, uid + ext)

    # Save uploaded file to disk
    with open(original_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Run YOLO prediction
    results = model(original_path, device="cpu")
    annotated_frame = results[0].plot()
    annotated_image = Image.fromarray(annotated_frame)
    annotated_image.save(predicted_path)

    # Save session metadata
    save_prediction_session(
        db=db,
        uid=uid,
        original_image=original_path,
        predicted_image=predicted_path,
        user_id=user_id
    )

    # Save detections
    detected_labels = []
    for box in results[0].boxes:
        label_idx = int(box.cls[0].item())
        label = model.names[label_idx]
        score = float(box.conf[0])
        bbox = box.xyxy[0].tolist()

        save_detection_object(
            db=db,
            prediction_uid=uid,
            label=label,
            score=score,
            box=str(bbox)
        )
        detected_labels.append(label)

    # Prepare response
    processing_time = round(time.time() - start_time, 2)
    return {
        "prediction_uid": uid,
        "detection_count": len(results[0].boxes),
        "labels": detected_labels,
        "time_took": processing_time,
    }