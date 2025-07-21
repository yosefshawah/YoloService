import unittest
import base64
from fastapi.testclient import TestClient
from app import app
from io import BytesIO
from PIL import Image
import sqlite3
import os

TEST_USER = "testuser"
TEST_PASS = "testpass"
DB_PATH = os.path.join(os.path.dirname(__file__), "../predictions.db")

def get_auth_header(username=TEST_USER, password=TEST_PASS):
    encoded = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"Authorization": f"Basic {encoded}"}

def create_dummy_image_bytes():
    img = Image.open("beatles.jpeg")  # Replace with a valid image
    img_bytes = BytesIO()
    img.save(img_bytes, format="JPEG")
    img_bytes.seek(0)
    return img_bytes

class TestPredictEndpoint(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_predict_with_real_image(self):
        img_file = create_dummy_image_bytes()
        response = self.client.post(
            "/predict",
            files={"file": ("beatles.jpg", img_file, "image/jpeg")},
            headers=get_auth_header()
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("prediction_uid", data)
        self.assertIn("labels", data)
        self.assertIn("detection_count", data)
        self.assertIn("time_took", data)

    def test_predict_without_auth_uses_anonymous(self):
        img_file = create_dummy_image_bytes()
        response = self.client.post(
            "/predict",
            files={"file": ("beatles.jpg", img_file, "image/jpeg")}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("prediction_uid", data)
        self.assertIn("labels", data)
        self.assertIn("detection_count", data)
        self.assertIn("time_took", data)


if __name__ == "__main__":
    unittest.main()
