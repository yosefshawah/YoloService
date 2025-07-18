# test_auth.py
import unittest
import base64
import sqlite3
import os
from fastapi.testclient import TestClient
from app import app, init_db, DB_PATH
from io import BytesIO
from PIL import Image

TEST_USER = "testuser"
TEST_PASS = "testpass"
ENCODED_CREDENTIALS = base64.b64encode(f"{TEST_USER}:{TEST_PASS}".encode()).decode()
AUTH_HEADER = {"Authorization": f"Basic {ENCODED_CREDENTIALS}"}


def create_dummy_image_bytes():
    img = Image.new("RGB", (100, 100), color="blue")
    img_bytes = BytesIO()
    img.save(img_bytes, format="JPEG")
    img_bytes.seek(0)  # Reset cursor to beginning
    return img_bytes

class TestAuthEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        init_db()

        # Insert a test user
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("INSERT OR IGNORE INTO users (username, password) VALUES (?, ?)",
                         (TEST_USER, TEST_PASS))
            conn.commit()

    #should work always not dependant with auths.
    def test_status_endpoint_public(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)

    def test_predict_with_auth_user(self):
        # Create a dummy image in memory
        img_file = create_dummy_image_bytes()

        response = self.client.post(
            "/predict",
            files={"file": ("dummy.jpg", img_file, "image/jpeg")},
            headers=AUTH_HEADER
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("prediction_uid", response.json())
        
    def test_predict_null_user(self):
        img_file = create_dummy_image_bytes()

        # Send request without Authorization header
        response = self.client.post(
            "/predict",
            files={"file": ("dummy.jpg", img_file, "image/jpeg")}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("prediction_uid", response.json())
        

   
    def test_only_owner_can_access_prediction(self):
        image_file = create_dummy_image_bytes()
        create_response = self.client.post(
            "/predict",
            files={"file": ("test.jpg", image_file, "image/jpeg")},
            headers=AUTH_HEADER
        )
        self.assertEqual(create_response.status_code, 200)
        uid = create_response.json()["prediction_uid"]

        # Access prediction as a second (different) valid user
        second_user = "seconduser"
        second_pass = "secondpass"
        second_creds = base64.b64encode(f"{second_user}:{second_pass}".encode()).decode()
        second_auth_header = {"Authorization": f"Basic {second_creds}"}

        get_response_other = self.client.get(f"/prediction/{uid}", headers=second_auth_header)

        self.assertEqual(get_response_other.status_code, 401)  


    def test_invalid_auth(self):
        # Use correct username, but incorrect password
        wrong_pass_credentials = base64.b64encode("testuser:wrongpass".encode()).decode()
        bad_header = {"Authorization": f"Basic {wrong_pass_credentials}"}
        
        img_file = create_dummy_image_bytes()
        # Try accessing a protected endpoint with wrong auth
        response = self.client.post("/predict", files={"file": ("dummy.jpg", img_file, "image/jpeg")}, headers=bad_header)
        self.assertEqual(response.status_code, 401)

if __name__ == "__main__":
    unittest.main()
