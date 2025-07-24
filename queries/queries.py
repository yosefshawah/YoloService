from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from models.models import PredictionSession
from sqlalchemy.orm import Session
from models.models import DetectionObject

def save_prediction_session(db: Session, uid: str, original_image: str, predicted_image: str, user_id: int):
    session = PredictionSession(
        uid=uid,
        original_image=original_image,
        predicted_image=predicted_image,
        user_id=user_id
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session




def save_detection_object(
    db: Session,
    prediction_uid: str,
    label: str,
    score: float,
    box: str
):
    detection = DetectionObject(
        prediction_uid=prediction_uid,
        label=label,
        score=score,
        box=box
    )
    
    db.add(detection)
    db.commit()
    db.refresh(detection)
    return detection



def query_sessions_by_label(db: Session, label: str, user_id: int):
    return (
        db.query(PredictionSession)
        .join(PredictionSession.detections)
        .filter(DetectionObject.label == label, PredictionSession.user_id == user_id)
        .distinct()
        .all()
    )
    
def query_sessions_by_min_score(db: Session, min_score: float, user_id: int):
    return (
        db.query(PredictionSession)
        .join(PredictionSession.detections)
        .filter(
            DetectionObject.score >= min_score,
            PredictionSession.user_id == user_id
        )
        .distinct()
        .all()
    )
    


def query_prediction_image_by_uid(db: Session, uid: str):
    return db.query(PredictionSession).filter(PredictionSession.uid == uid).first()




def query_prediction_count_last_week(db: Session):
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    return db.query(func.count(PredictionSession.uid)).filter(
        PredictionSession.timestamp >= seven_days_ago
    ).scalar()
    
    
    
def query_unique_labels_last_week(db: Session):
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    labels = (
        db.query(DetectionObject.label)
        .join(PredictionSession, DetectionObject.prediction_uid == PredictionSession.uid)
        .filter(PredictionSession.timestamp >= seven_days_ago)
        .distinct()
        .all()
    )
    # `labels` is list of tuples like [('person',), ('car',), ...]
    return [label[0] for label in labels]




def query_total_predictions_last_8_days(db: Session, user_id: int, time_threshold: datetime) -> int:
    return (
        db.query(PredictionSession)
        .filter(
            PredictionSession.user_id == user_id,
            PredictionSession.timestamp >= time_threshold
        )
        .count()
    )

def query_detection_objects_last_8_days(db: Session, user_id: int, time_threshold: datetime):
    return (
        db.query(DetectionObject.label, DetectionObject.score)
        .join(PredictionSession, DetectionObject.prediction_uid == PredictionSession.uid)
        .filter(
            PredictionSession.user_id == user_id,
            PredictionSession.timestamp >= time_threshold
        )
        .all()
    )
