from datetime import datetime, timedelta, timezone
from typing import Counter
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session  # not requests.Session!
from dependencies.auth import get_current_user_id
from queries.queries import query_detection_objects_last_8_days, query_sessions_by_min_score, query_total_predictions_last_8_days
from database.db import get_db  # make sure this is imported
from queries.queries import query_prediction_count_last_week

router = APIRouter()


from fastapi import Depends
from requests import Session

from dependencies.auth import get_current_user_id
from queries.queries import query_sessions_by_min_score


@router.get("/predictions/score/{min_score}")
def get_predictions_by_score(
    min_score: float,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    sessions = query_sessions_by_min_score(db, min_score, user_id)
    return [{"uid": session.uid, "timestamp": session.timestamp} for session in sessions]






@router.get("/predictions/count")
def get_prediction_count_last_week(db: Session = Depends(get_db)):
    count = query_prediction_count_last_week(db)
    return {"count": count}



@router.get("/stats")
def get_prediction_statistics_last_week(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    time_threshold = datetime.now(timezone.utc) - timedelta(days=8)

    total = query_total_predictions_last_8_days(db, user_id, time_threshold)
    rows = query_detection_objects_last_8_days(db, user_id, time_threshold)

    scores = [row.score for row in rows]
    labels = [row.label for row in rows]

    avg_score = round(sum(scores) / len(scores), 4) if scores else 0.0
    label_counts = dict(Counter(labels))

    return {
        "total_predictions": total,
        "average_confidence_score": avg_score,
        "most_common_labels": label_counts,
    }
