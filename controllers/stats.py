from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session  # not requests.Session!
from dependencies.auth import get_current_user_id
from queries.queries import query_sessions_by_min_score
from database.db import get_db  # make sure this is imported

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