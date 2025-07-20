import os
import unittest
import sqlite3
import uuid
from fastapi.testclient import TestClient
from app import app, init_db, DB_PATH
from dependencies.auth import get_current_user_id

TEST_USER = "testuser_score"
TEST_PASS = "testpass"
TEST_USER_ID = 2001

SECOND_USER = "seconduser_score"
SECOND_PASS = "secondpass"
SECOND_USER_ID = 2002


class TestGetPredictionsByScore(unittest.TestCase):
    def setUp(self):
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
        init_db()

        self.uid_high_score = str(uuid.uuid4())
        self.uid_low_score = str(uuid.uuid4())

        with sqlite3.connect(DB_PATH) as conn:
            # Insert test users
            conn.execute(
                "INSERT INTO users (id, username, password) VALUES (?, ?, ?)",
                (TEST_USER_ID, TEST_USER, TEST_PASS)
            )
            conn.execute(
                "INSERT INTO users (id, username, password) VALUES (?, ?, ?)",
                (SECOND_USER_ID, SECOND_USER, SECOND_PASS)
            )

            # Insert prediction sessions and detection objects for TEST_USER
            conn.execute(
                "INSERT INTO prediction_sessions (uid, user_id, timestamp, original_image, predicted_image) VALUES (?, ?, CURRENT_TIMESTAMP, ?, ?)",
                (self.uid_high_score, TEST_USER_ID, "img1.jpg", "pred1.jpg")
            )
            conn.execute(
                "INSERT INTO detection_objects (prediction_uid, label, score, box) VALUES (?, ?, ?, ?)",
                (self.uid_high_score, "dog", 0.95, "[1,2,3,4]")
            )

            conn.execute(
                "INSERT INTO prediction_sessions (uid, user_id, timestamp, original_image, predicted_image) VALUES (?, ?, CURRENT_TIMESTAMP, ?, ?)",
                (self.uid_low_score, TEST_USER_ID, "img2.jpg", "pred2.jpg")
            )
            conn.execute(
                "INSERT INTO detection_objects (prediction_uid, label, score, box) VALUES (?, ?, ?, ?)",
                (self.uid_low_score, "cat", 0.4, "[5,6,7,8]")
            )

            # Insert unrelated session for SECOND_USER
            other_uid = str(uuid.uuid4())
            conn.execute(
                "INSERT INTO prediction_sessions (uid, user_id, timestamp, original_image, predicted_image) VALUES (?, ?, CURRENT_TIMESTAMP, ?, ?)",
                (other_uid, SECOND_USER_ID, "img3.jpg", "pred3.jpg")
            )
            conn.execute(
                "INSERT INTO detection_objects (prediction_uid, label, score, box) VALUES (?, ?, ?, ?)",
                (other_uid, "fox", 0.99, "[0,0,0,0]")
            )

            conn.commit()

        self.client = TestClient(app)
        app.dependency_overrides[get_current_user_id] = lambda: TEST_USER_ID

    def test_get_predictions_above_threshold(self):
        headers = {"Authorization": "Basic dummy"}
        response = self.client.get("/predictions/score/0.9", headers=headers)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["uid"], self.uid_high_score)

    def test_get_predictions_none_match(self):
        headers = {"Authorization": "Basic dummy"}
        response = self.client.get("/predictions/score/0.99", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_predictions_filtered_by_user(self):
        # Switch to second user (who has a high-score detection)
        app.dependency_overrides[get_current_user_id] = lambda: SECOND_USER_ID
        headers = {"Authorization": "Basic dummy"}

        response = self.client.get("/predictions/score/0.9", headers=headers)
        self.assertEqual(response.status_code, 200)

        # Should not return TEST_USER's predictions
        self.assertEqual(len(response.json()), 1)
        self.assertNotEqual(response.json()[0]["uid"], self.uid_high_score)


if __name__ == "__main__":
    unittest.main()
