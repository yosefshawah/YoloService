from sqlalchemy.orm import Session
from models.models import PredictionSession, DetectionObject

def get_prediction_session(db: Session, uid: str, user_id: int):
    return db.query(PredictionSession).filter(
        PredictionSession.uid == uid,
        PredictionSession.user_id == user_id
    ).first()

def get_detection_objects(db: Session, prediction_uid: str):
    return db.query(DetectionObject).filter(
        DetectionObject.prediction_uid == prediction_uid
    ).all()
