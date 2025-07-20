import os
import unittest
import sqlite3
import uuid
from fastapi.testclient import TestClient
from app import app, init_db, DB_PATH
from dependencies.auth import get_current_user_id

# Dummy user IDs for testing
TEST_USER_ID = 3001
OTHER_USER_ID = 3002

class TestDeletePredictionEndpoint(unittest.TestCase):
    def setUp(self):
        # Clear DB file and initialize fresh schema
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
        init_db()

        # Create uploads dirs for images
        self.original_dir = os.path.join("uploads", "original")
        self.predicted_dir = os.path.join("uploads", "predicted")
        os.makedirs(self.original_dir, exist_ok=True)
        os.makedirs(self.predicted_dir, exist_ok=True)

        # Prepare dummy prediction data owned by TEST_USER_ID
        self.uid = str(uuid.uuid4())
        self.original_path = os.path.join(self.original_dir, f"{self.uid}.jpg")
        self.predicted_path = os.path.join(self.predicted_dir, f"{self.uid}.jpg")

        # Create dummy image files
        with open(self.original_path, "wb") as f:
            f.write(b"original image data")
        with open(self.predicted_path, "wb") as f:
            f.write(b"predicted image data")

        # Insert a prediction session owned by TEST_USER_ID
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "INSERT INTO prediction_sessions (uid, user_id, timestamp, original_image, predicted_image) VALUES (?, ?, CURRENT_TIMESTAMP, ?, ?)",
                (self.uid, TEST_USER_ID, self.original_path, self.predicted_path),
            )
            conn.commit()

        # Create a prediction session owned by OTHER_USER_ID to test permission denial
        self.other_uid = str(uuid.uuid4())
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "INSERT INTO prediction_sessions (uid, user_id, timestamp, original_image, predicted_image) VALUES (?, ?, CURRENT_TIMESTAMP, ?, ?)",
                (self.other_uid, OTHER_USER_ID, self.original_path, self.predicted_path),
            )
            conn.commit()

        self.client = TestClient(app)

        # Override the auth dependency to simulate logged in user as TEST_USER_ID by default
        app.dependency_overrides[get_current_user_id] = lambda: TEST_USER_ID


        def test_delete_valid_prediction(self):
            # User deletes their own prediction successfully
            response = self.client.delete(f"/prediction/{self.uid}")
            self.assertEqual(response.status_code, 200)
            self.assertIn("deleted", response.json().get("detail", "").lower())

            # Confirm DB record deleted
            with sqlite3.connect(DB_PATH) as conn:
                row = conn.execute("SELECT * FROM prediction_sessions WHERE uid = ?", (self.uid,)).fetchone()
                self.assertIsNone(row)

            # Confirm files are deleted
            self.assertFalse(os.path.exists(self.original_path))
            self.assertFalse(os.path.exists(self.predicted_path))

    def test_delete_prediction_not_owned_by_user(self):
        # Attempt to delete prediction owned by OTHER_USER_ID (should be denied)
        response = self.client.delete(f"/prediction/{self.other_uid}")
        self.assertEqual(response.status_code, 404)
        self.assertIn("not found", response.json().get("detail", "").lower())

        # Ensure DB record still exists
        with sqlite3.connect(DB_PATH) as conn:
            row = conn.execute("SELECT * FROM prediction_sessions WHERE uid = ?", (self.other_uid,)).fetchone()
            self.assertIsNotNone(row)

    def test_delete_prediction_not_exist(self):
        # Attempt to delete a non-existent prediction
        fake_uid = str(uuid.uuid4())
        response = self.client.delete(f"/prediction/{fake_uid}")
        self.assertEqual(response.status_code, 404)
        self.assertIn("not found", response.json().get("detail", "").lower())
        
    def test_delete_files_raises_exception(self):
        # Files must exist for the endpoint to try deleting them
        with open(self.original_path, "wb") as f:
            f.write(b"original image data")
        with open(self.predicted_path, "wb") as f:
            f.write(b"predicted image data")

        # Temporarily rename os.remove so it raises an error
        original_remove = os.remove
        def raise_error(path):
            raise OSError("forced error")

        os.remove = raise_error

        try:
            response = self.client.delete(f"/prediction/{self.uid}")
            self.assertEqual(response.status_code, 200)
            self.assertIn("deleted", response.json().get("detail", "").lower())
        finally:
            # Restore original os.remove so other tests aren't affected
            os.remove = original_remove

        
