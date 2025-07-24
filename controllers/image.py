# controllers/images.py

import os
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from requests import Session

from database.db import get_db
from queries.queries import query_prediction_image_by_uid

router = APIRouter()

@router.get("/image/{type}/{filename}")
def get_image(type: str, filename: str):
    """
    Get image by type and filename
    """
    if type not in ["original", "predicted"]:
        raise HTTPException(status_code=400, detail="Invalid image type")
    
    path = os.path.join("uploads", type, filename)
    
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Image not found")

    return FileResponse(path)



@router.get("/prediction/{uid}/image")
def get_prediction_image(uid: str, request: Request, db: Session = Depends(get_db)):
    """
    Get prediction image by UID.
    """
    accept = request.headers.get("accept", "")

    session = query_prediction_image_by_uid(db, uid)
    if not session:
        raise HTTPException(status_code=404, detail="Prediction not found")

    image_path = session.predicted_image

    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="Predicted image file not found")

    if "image/png" in accept:
        return FileResponse(image_path, media_type="image/png")
    elif "image/jpeg" in accept or "image/jpg" in accept:
        return FileResponse(image_path, media_type="image/jpeg")
    else:
        raise HTTPException(
            status_code=406, detail="Client does not accept an image format"
        )
