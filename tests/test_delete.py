# test_delete.py
import unittest
from fastapi.testclient import TestClient
from PIL import Image
import sqlite3
import os
import time
from app import app, init_db, DB_PATH

UPLOAD_DIR = "uploads/original"
PREDICTED_DIR = "uploads/predicted"


class TestDeletePredictionEndpoint(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        init_db()

        os.makedirs(UPLOAD_DIR, exist_ok=True)
        os.makedirs(PREDICTED_DIR, exist_ok=True)

        self.uid = "test-uid"
        self.original_filename = os.path.join(UPLOAD_DIR, f"{self.uid}.jpg")
        self.predicted_filename = os.path.join(PREDICTED_DIR, f"{self.uid}.jpg")

        for path in [self.original_filename, self.predicted_filename]:
            img = Image.new("RGB", (100, 100), color="blue")
            img.save(path, format="JPEG")

        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                """
                INSERT INTO prediction_sessions (uid, original_image, predicted_image)
                VALUES (?, ?, ?)""",
                (self.uid, self.original_filename, self.predicted_filename),
            )
            conn.execute(
                """
                INSERT INTO detection_objects (prediction_uid, label, score, box)
                VALUES (?, ?, ?, ?)""",
                (self.uid, "test-label", 0.99, "[0,0,10,10]"),
            )

    def tearDown(self):
        # ❌ Don't remove the whole DB
        # ✅ Just delete the test rows and test files

        # Clean test DB entries
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "DELETE FROM detection_objects WHERE prediction_uid = ?", (self.uid,)
            )
            conn.execute("DELETE FROM prediction_sessions WHERE uid = ?", (self.uid,))
            conn.commit()

        # Remove only test files
        for path in [self.original_filename, self.predicted_filename]:
            if os.path.exists(path):
                os.remove(path)

    def test_delete_prediction_with_visible_delay(self):
        """Test DELETE with delay to observe file existence before deletion"""

        self.assertTrue(os.path.exists(self.original_filename))
        self.assertTrue(os.path.exists(self.predicted_filename))

        print(
            "\n🕒 Waiting 3 seconds to inspect files in 'uploads/original' and 'uploads/predicted'..."
        )
        time.sleep(3)

        response = self.client.delete(f"/prediction/{self.uid}")
        self.assertEqual(response.status_code, 200)
        self.assertIn("deleted", response.json()["detail"])

        self.assertFalse(os.path.exists(self.original_filename))
        self.assertFalse(os.path.exists(self.predicted_filename))

        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM prediction_sessions WHERE uid = ?", (self.uid,))
            self.assertIsNone(cur.fetchone())

            cur.execute(
                "SELECT * FROM detection_objects WHERE prediction_uid = ?", (self.uid,)
            )
            self.assertIsNone(cur.fetchone())


if __name__ == "__main__":
    unittest.main()
