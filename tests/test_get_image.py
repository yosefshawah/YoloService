import os
import unittest
from fastapi.testclient import TestClient
from fastapi import status
from app import app  
from shutil import rmtree

class TestGetImageEndpoint(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.test_image_name = "test_image.jpg"
        self.original_path = os.path.join("uploads", "original")
        self.predicted_path = os.path.join("uploads", "predicted")

        # Create necessary directories and test file
        os.makedirs(self.original_path, exist_ok=True)
        os.makedirs(self.predicted_path, exist_ok=True)
        with open(os.path.join(self.original_path, self.test_image_name), "wb") as f:
            f.write(b"dummy image content")

  

    def test_get_original_image_success(self):
        response = self.client.get(f"/image/original/{self.test_image_name}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"dummy image content")

    def test_get_predicted_image_not_found(self):
        response = self.client.get(f"/image/predicted/nonexistent.jpg")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Image not found")

    def test_invalid_type(self):
        response = self.client.get(f"/image/invalidtype/{self.test_image_name}")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Invalid image type")


if __name__ == "__main__":
    unittest.main()
