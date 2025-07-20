import os
import sqlite3
import uuid
import base64
import json
from datetime import datetime
import unittest
from fastapi.testclient import TestClient
from app import app, init_db, DB_PATH
from dependencies.auth import get_current_user_id

TEST_USERNAME = "testuser"
TEST_PASSWORD = "testpass"
ENCODED_CREDENTIALS = base64.b64encode(f"{TEST_USERNAME}:{TEST_PASSWORD}".encode()).decode()
AUTH_HEADER = {"Authorization": f"Basic {ENCODED_CREDENTIALS}"}


class TestLabelEndpoint(unittest.TestCase):
    def setUp(self):
        # Remove existing DB to start fresh
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)

        # Initialize DB and tables
        init_db()

        # Insert test user with fixed user_id = 1
        self.user_id = 1
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "INSERT INTO users (id, username, password) VALUES (?, ?, ?)",
                (self.user_id, TEST_USERNAME, TEST_PASSWORD),
            )
            conn.commit()

        # Create TestClient for API requests
        self.client = TestClient(app)

        # Override dependency to always return our test user_id for auth
        app.dependency_overrides[get_current_user_id] = lambda: self.user_id

    def setup_test_prediction(self, label):
        uid = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()

        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "INSERT INTO prediction_sessions (uid, timestamp, user_id) VALUES (?, ?, ?)",
                (uid, timestamp, self.user_id),
            )
            conn.execute(
                "INSERT INTO detection_objects (prediction_uid, label, score, box) VALUES (?, ?, ?, ?)",
                (uid, label, 0.95, json.dumps([50, 50, 100, 100])),
            )
            conn.commit()

        return uid, timestamp

    def test_get_predictions_by_label(self):
        label = "car"
        uid, timestamp = self.setup_test_prediction(label)

        response = self.client.get(f"/predictions/label/{label}", headers=AUTH_HEADER)
        self.assertEqual(response.status_code, 200)

        predictions = response.json()

        # Timestamp strings may differ slightly, so we match only the start
        self.assertTrue(
            any(
                p["uid"] == uid and p["timestamp"].startswith(timestamp[:19])
                for p in predictions
            ),
            f"Expected prediction with uid {uid} not found in response: {predictions}",
        )


if __name__ == "__main__":
    unittest.main()
