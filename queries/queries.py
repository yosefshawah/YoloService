
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

