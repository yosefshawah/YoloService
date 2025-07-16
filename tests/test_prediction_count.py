import unittest
from fastapi.testclient import TestClient
from app import app
import sqlite3
from datetime import datetime, timedelta

DB_PATH = "predictions.db"


class TestPredictionCount(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

        # Clean and insert controlled test data
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("DELETE FROM prediction_sessions")

            # Insert a recent prediction (within 7 days)
            conn.execute(
                """
                INSERT INTO prediction_sessions (uid, timestamp, original_image, predicted_image)
                VALUES (?, ?, ?, ?)
            """,
                (
                    "recent-id",
                    datetime.utcnow().isoformat(),
                    "recent_original.jpg",
                    "recent_predicted.jpg",
                ),
            )

            # Insert an old prediction (more than 7 days ago)
            conn.execute(
                """
                INSERT INTO prediction_sessions (uid, timestamp, original_image, predicted_image)
                VALUES (?, ?, ?, ?)
            """,
                (
                    "old-id",
                    (datetime.utcnow() - timedelta(days=10)).isoformat(),
                    "old_original.jpg",
                    "old_predicted.jpg",
                ),
            )

    def test_prediction_count_format(self):
        """Check response format and status"""
        response = self.client.get("/predictions/count")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("count", data)
        self.assertIsInstance(data["count"], int)
        self.assertGreaterEqual(data["count"], 0)

    def test_prediction_count_last_7_days(self):
        """Ensure only recent predictions are counted"""
        response = self.client.get("/predictions/count")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 1)  # Only the recent one should be counted
