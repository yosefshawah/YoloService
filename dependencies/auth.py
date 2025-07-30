# dependencies/auth.py

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from database.db import get_db
from models.models import User

security = HTTPBasic(auto_error=False)

def ensure_anonymous_user(db: Session):
    anonymous_user = db.query(User).filter_by(username="__anonymous__").first()
    if not anonymous_user:
        new_user = User(username="__anonymous__", password="__none__")
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user.id
    return anonymous_user.id

def get_current_user_id(
    request: Request,
    credentials: Optional[HTTPBasicCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    if credentials is None or (not credentials.username and not credentials.password):
        return ensure_anonymous_user(db)

    username = credentials.username
    password = credentials.password

    if username and not password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Password is required when username is provided."
        )

    user = db.query(User).filter_by(username=username).first()

    if user:
        if user.password == password:
            return user.id
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password."
        )
    else:
        # Auto-create user
        try:
            new_user = User(username=username, password=password)
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            return new_user.id
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=500,
                detail="User creation failed due to integrity error."
            )
