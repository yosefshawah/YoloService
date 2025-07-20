import os
import unittest
import sqlite3
import uuid
from fastapi.testclient import TestClient
from app import app, init_db, DB_PATH
from shutil import rmtree


class TestGetPredictionImageEndpoint(unittest.TestCase):
    def setUp(self):
        # Clean and initialize DB
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
        init_db()

        # Setup test image
        self.uid = str(uuid.uuid4())
        self.image_path = os.path.join("uploads", "predicted", f"{self.uid}.jpg")
        os.makedirs(os.path.dirname(self.image_path), exist_ok=True)
        with open(self.image_path, "wb") as f:
            f.write(b"fake jpeg data")

        # Insert test session into DB
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "INSERT INTO prediction_sessions (uid, user_id, timestamp, original_image, predicted_image) VALUES (?, ?, CURRENT_TIMESTAMP, ?, ?)",
                (self.uid, 1, "orig.jpg", self.image_path)
            )
            conn.commit()

        self.client = TestClient(app)

    def test_valid_jpeg_request(self):
        headers = {"Accept": "image/jpeg"}
        response = self.client.get(f"/prediction/{self.uid}/image", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "image/jpeg")
        self.assertEqual(response.content, b"fake jpeg data")

    def test_prediction_uid_not_found(self):
        fake_uid = str(uuid.uuid4())
        headers = {"Accept": "image/jpeg"}
        response = self.client.get(f"/prediction/{fake_uid}/image", headers=headers)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Prediction not found")

    def test_missing_image_file(self):
        # Delete the file from disk
        os.remove(self.image_path)
        headers = {"Accept": "image/jpeg"}
        response = self.client.get(f"/prediction/{self.uid}/image", headers=headers)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Predicted image file not found")

    def test_unsupported_accept_header(self):
        headers = {"Accept": "application/json"}
        response = self.client.get(f"/prediction/{self.uid}/image", headers=headers)
        self.assertEqual(response.status_code, 406)
        self.assertEqual(response.json()["detail"], "Client does not accept an image format")

    def test_valid_png_request(self):
        # First, create a fake PNG file
        png_path = os.path.join("uploads", "predicted", f"{self.uid}.png")
        with open(png_path, "wb") as f:
            f.write(b"fake png data")

        # Update the database to use the PNG path instead
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "UPDATE prediction_sessions SET predicted_image = ? WHERE uid = ?",
                (png_path, self.uid)
            )
            conn.commit()

        headers = {"Accept": "image/png"}
        response = self.client.get(f"/prediction/{self.uid}/image", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "image/png")
        self.assertEqual(response.content, b"fake png data")


if __name__ == "__main__":
    unittest.main()
