# dependencies/auth.py

import sqlite3
import os
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "predictions.db")
security = HTTPBasic()

def ensure_users_table():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            );
        """)

def get_user_by_username(cursor, username):
    cursor.execute("SELECT id, password FROM users WHERE username = ?", (username,))
    return cursor.fetchone()

def create_user(cursor, username, password):
    cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
    return cursor.lastrowid

def get_anonymous_user_id() -> int:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO users (username, password)
            VALUES ("__anonymous__", "__none__");
        """)
        conn.commit()
        cursor.execute("SELECT id FROM users WHERE username = '__anonymous__'")
        return cursor.fetchone()[0]

def get_current_user_id(credentials: HTTPBasicCredentials = Depends(security)) -> int:
    """
    Auth logic equivalent to your middleware, triggered per request via Depends
    """
    ensure_users_table()
    username = credentials.username
    password = credentials.password

    if not username and not password:
        return get_anonymous_user_id()

    if username and not password:
        raise HTTPException(status_code=401, detail="Password is required when username is provided.")

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        user = get_user_by_username(cursor, username)

        if user:
            stored_password = user[1]
            if stored_password == password:
                return user[0]
            raise HTTPException(status_code=403, detail="Incorrect password.")
        else:
            # Auto-create user
            try:
                user_id = create_user(cursor, username, password)
                conn.commit()
                return user_id
            except sqlite3.IntegrityError:
                raise HTTPException(status_code=500, detail="User creation failed.")
