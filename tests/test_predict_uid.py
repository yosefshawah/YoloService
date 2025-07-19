import os
import unittest
import sqlite3
import uuid
from fastapi.testclient import TestClient
from app import app, init_db, DB_PATH
from dependencies.auth import get_current_user_id

TEST_USER = "testuser_fullcode"
TEST_PASS = "testpass"
TEST_USER_ID = 1001

SECOND_USER = "seconduser_fullcode"
SECOND_PASS = "secondpass"
SECOND_USER_ID = 1002


class TestGetPredictionByUID(unittest.TestCase):
    def setUp(self):
        # Remove DB file if exists to start fresh
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)

        # Initialize DB tables
        init_db()

        # Insert test users and initial prediction data
        with sqlite3.connect(DB_PATH) as conn:
            # Insert users
            conn.execute(
                "INSERT INTO users (id, username, password) VALUES (?, ?, ?)",
                (TEST_USER_ID, TEST_USER, TEST_PASS),
            )
            conn.execute(
                "INSERT INTO users (id, username, password) VALUES (?, ?, ?)",
                (SECOND_USER_ID, SECOND_USER, SECOND_PASS),
            )

            # Insert prediction session for TEST_USER
            self.uid = str(uuid.uuid4())
            conn.execute(
                "INSERT INTO prediction_sessions (uid, user_id, timestamp, original_image, predicted_image) VALUES (?, ?, CURRENT_TIMESTAMP, ?, ?)",
                (self.uid, TEST_USER_ID, "original.jpg", "predicted.jpg"),
            )
            conn.execute(
                "INSERT INTO detection_objects (prediction_uid, label, score, box) VALUES (?, ?, ?, ?)",
                (self.uid, "cat", 0.95, "[10,20,30,40]"),
            )
            conn.commit()

        # Create TestClient and override auth dependency to simulate TEST_USER_ID
        self.client = TestClient(app)
        app.dependency_overrides[get_current_user_id] = lambda: TEST_USER_ID

    def tearDown(self):
        # Clear dependency overrides to avoid leakage between tests
        app.dependency_overrides = {}

    def test_get_prediction_success(self):
        headers = {"Authorization": "Basic dummy"}  # Auth overridden anyway
        response = self.client.get(f"/prediction/{self.uid}", headers=headers)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["uid"], self.uid)
        self.assertEqual(data["original_image"], "original.jpg")
        self.assertEqual(data["predicted_image"], "predicted.jpg")
        self.assertIsInstance(data["detection_objects"], list)
        self.assertGreater(len(data["detection_objects"]), 0)
        self.assertEqual(data["detection_objects"][0]["label"], "cat")

    def test_get_prediction_unauthorized(self):
        # Override auth dependency to simulate second user
        app.dependency_overrides[get_current_user_id] = lambda: SECOND_USER_ID

        headers = {"Authorization": "Basic dummy"}
        response = self.client.get(f"/prediction/{self.uid}", headers=headers)
        self.assertEqual(response.status_code, 401)
        self.assertIn("Unauthorized", response.json().get("detail", ""))

    def test_get_prediction_not_found(self):
        headers = {"Authorization": "Basic dummy"}
        response = self.client.get("/prediction/non-existent-uid", headers=headers)
        self.assertEqual(response.status_code, 401)
        self.assertIn("Unauthorized", response.json().get("detail", ""))


if __name__ == "__main__":
    unittest.main()
