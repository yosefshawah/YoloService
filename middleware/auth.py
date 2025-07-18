# middleware/auth.py
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "predictions.db")

# Ensure the users table exists
def ensure_users_table():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            );
        """)

# Check if user exists; if not, create them
def ensure_user_exists(username: str, password: str) -> int:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username = ? AND password = ?", (username, password))
        user = cursor.fetchone()

        if user:
            return user[0]  # Return existing user ID

        try:
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
            return cursor.lastrowid  # Return newly created user ID
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=403, detail="Username exists with different password")

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        username = request.headers.get("X-Username")
        password = request.headers.get("X-Password")

        if not username or not password:
            raise HTTPException(status_code=401, detail="Missing authentication headers")

        ensure_users_table()
        user_id = ensure_user_exists(username, password)
        request.state.user_id = user_id


        response = await call_next(request)
        return response
