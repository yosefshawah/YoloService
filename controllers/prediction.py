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
from database.queries import get_detection_objects, get_prediction_session
from dependencies.auth import get_current_user_id
from queries.queries import query_sessions_by_label, save_detection_object, save_prediction_session

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
    
    
@router.get("/prediction/{uid}")
def get_prediction_by_uid(
    uid: str,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    session = get_prediction_session(db, uid, user_id)
    if not session:
        raise HTTPException(status_code=401, detail="Unauthorized or prediction not found")

    objects = get_detection_objects(db, uid)

    return {
        "uid": session.uid,
        "timestamp": session.timestamp,
        "original_image": session.original_image,
        "predicted_image": session.predicted_image,
        "detection_objects": [
            {
                "id": obj.id,
                "label": obj.label,
                "score": obj.score,
                "box": obj.box,
            }
            for obj in objects
        ],
    }
    
    
@router.get("/predictions/label/{label}")
def get_predictions_by_label(
    label: str,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """
    Get prediction sessions for current user that contain objects with the specified label.
    """
    sessions = query_sessions_by_label(db, label, user_id)
    return [
        {"uid": session.uid, "timestamp": session.timestamp}
        for session in sessions
    ]