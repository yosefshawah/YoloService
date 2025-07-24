

from fastapi import APIRouter, Depends
from requests import Session

from database.db import get_db
from queries.queries import query_unique_labels_last_week
router = APIRouter()


@router.get("/labels")
def get_unique_labels_last_week(db: Session = Depends(get_db)):
    labels = query_unique_labels_last_week(db)
    return {"labels": labels}