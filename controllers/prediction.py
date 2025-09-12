import os
import shutil
import time
import uuid
from fastapi import APIRouter, Depends
from fastapi import HTTPException
from sqlalchemy.orm import Session
import torch
from botocore.config import Config
from services.s3 import get_s3_client

from database.db import get_db
from database.queries import get_detection_objects, get_prediction_session
from dependencies.auth import get_current_user_id
from models.models import DetectionObject, PredictionSession
from queries.queries import query_sessions_by_label, save_detection_object, save_prediction_session

router = APIRouter()

UPLOAD_DIR = "uploads/original"
PREDICTED_DIR = "uploads/predicted"
DB_PATH = "predictions.db"
CHATS_BASE_DIR = "uploads/chats"

AWS_REGION = os.getenv("AWS_REGION")
AWS_S3_BUCKET = os.getenv("AWS_S3_BUCKET")
aws_config = Config(region_name=AWS_REGION) if AWS_REGION else None
s3_client = get_s3_client()

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(PREDICTED_DIR, exist_ok=True)
torch.cuda.is_available = lambda: False



"""
The synchronous POST /predict endpoint has been removed.

Predictions are now handled asynchronously via RabbitMQ by the standalone
worker in `receive.py`. This router continues to serve read-only endpoints
for fetching prediction data.
"""
    
    
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
    
    


@router.delete("/prediction/{uid}")
async def delete_prediction(
    uid: str, 
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    """Delete a prediction and its associated files"""
    
    # Find the prediction
    prediction = db.query(PredictionSession).filter_by(
        uid=uid, 
        user_id=current_user_id
    ).first()
    
    if not prediction:
        raise HTTPException(status_code=404, detail="Prediction not found")
    
    # Delete associated detection objects
    db.query(DetectionObject).filter(
        DetectionObject.prediction_uid == prediction.uid
    ).delete()
    
    # Delete files if they exist
    if prediction.original_image and os.path.exists(prediction.original_image):
        os.remove(prediction.original_image)
    
    if prediction.predicted_image and os.path.exists(prediction.predicted_image):
        os.remove(prediction.predicted_image)
    
    # Delete the prediction from database
    db.delete(prediction)
    db.commit()
    
    return {"message": "Prediction deleted successfully"}


