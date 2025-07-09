import unittest
import sqlite3
from fastapi.testclient import TestClient
from app import app, DB_PATH  # Adjust if app is named differently

class TestStatsEndpoint(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.test_uid = "stats-test-uid"

        # Insert dummy prediction and detections
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO prediction_sessions (uid, original_image, predicted_image, timestamp)
                VALUES (?, 'uploads/original/dummy.jpg', 'uploads/predicted/dummy.jpg', datetime('now'))
            """, (self.test_uid,))
            conn.execute("""
                INSERT INTO detection_objects (prediction_uid, label, score, box)
                VALUES (?, 'dog', 0.90, '[0,0,10,10]'),
                       (?, 'dog', 0.80, '[0,0,10,10]'),
                       (?, 'cat', 0.85, '[0,0,10,10]')
            """, (self.test_uid, self.test_uid, self.test_uid))
            conn.commit()

    def tearDown(self):
        # Clean up test data
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("DELETE FROM detection_objects WHERE prediction_uid = ?", (self.test_uid,))
            conn.execute("DELETE FROM prediction_sessions WHERE uid = ?", (self.test_uid,))
            conn.commit()

    def test_stats_endpoint_structure_and_values(self):
        response = self.client.get("/stats")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Check required keys
        self.assertIn("total_predictions", data)
        self.assertIn("average_confidence_score", data)
        self.assertIn("most_common_labels", data)

        # Validate types
        self.assertIsInstance(data["total_predictions"], int)
        self.assertIsInstance(data["average_confidence_score"], float)
        self.assertIsInstance(data["most_common_labels"], dict)

        # Check label counts
        self.assertGreaterEqual(data["most_common_labels"].get("dog", 0), 2)
        self.assertGreaterEqual(data["most_common_labels"].get("cat", 0), 1)

if __name__ == "__main__":
    unittest.main()
