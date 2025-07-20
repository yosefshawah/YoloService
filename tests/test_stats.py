import os
import unittest
import sqlite3
from fastapi.testclient import TestClient
from app import app, init_db, DB_PATH
from dependencies.auth import get_current_user_id

TEST_USER_ID = 123
OTHER_USER_ID = 456

class TestStatsEndpoint(unittest.TestCase):
    def setUp(self):
        # Remove DB if exists and re-init schema
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
        init_db()

        # Insert sample data for two users
        with sqlite3.connect(DB_PATH) as conn:
            # Two prediction sessions for TEST_USER_ID within last 8 days
            conn.execute(
                "INSERT INTO prediction_sessions (uid, user_id, timestamp, original_image, predicted_image) VALUES (?, ?, datetime('now', '-2 days'), ?, ?)",
                ("uid1", TEST_USER_ID, "orig1.jpg", "pred1.jpg")
            )
            conn.execute(
                "INSERT INTO prediction_sessions (uid, user_id, timestamp, original_image, predicted_image) VALUES (?, ?, datetime('now', '-5 days'), ?, ?)",
                ("uid2", TEST_USER_ID, "orig2.jpg", "pred2.jpg")
            )
            # One prediction session for OTHER_USER_ID within last 8 days
            conn.execute(
                "INSERT INTO prediction_sessions (uid, user_id, timestamp, original_image, predicted_image) VALUES (?, ?, datetime('now', '-3 days'), ?, ?)",
                ("uid3", OTHER_USER_ID, "orig3.jpg", "pred3.jpg")
            )

            # Detection objects for TEST_USER_ID predictions
            conn.execute(
                "INSERT INTO detection_objects (prediction_uid, label, score, box) VALUES (?, ?, ?, ?)",
                ("uid1", "cat", 0.9, "[1,2,3,4]")
            )
            conn.execute(
                "INSERT INTO detection_objects (prediction_uid, label, score, box) VALUES (?, ?, ?, ?)",
                ("uid2", "dog", 0.8, "[5,6,7,8]")
            )
            # Detection object for OTHER_USER_ID prediction
            conn.execute(
                "INSERT INTO detection_objects (prediction_uid, label, score, box) VALUES (?, ?, ?, ?)",
                ("uid3", "fox", 0.7, "[9,10,11,12]")
            )

            conn.commit()

        # Override the auth dependency to simulate TEST_USER_ID logged in
        app.dependency_overrides[get_current_user_id] = lambda: TEST_USER_ID
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides = {}

    def test_stats_returns_only_current_user_data(self):
        response = self.client.get("/stats")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Should only see stats for TEST_USER_ID's data
        self.assertEqual(data["total_predictions"], 2)
        expected_avg = round((0.9 + 0.8) / 2, 4)
        self.assertAlmostEqual(data["average_confidence_score"], expected_avg)
        self.assertEqual(data["most_common_labels"], {"cat": 1, "dog": 1})

        # Make sure OTHER_USER_ID's label is NOT included
        self.assertNotIn("fox", data["most_common_labels"])

if __name__ == "__main__":
    unittest.main()
