import os
import unittest
from unittest.mock import MagicMock, patch
from fastapi import Response
from fastapi.testclient import TestClient
from app import app  # adjust as needed
from database.db import get_db
from dependencies.auth import get_current_user_id

class TestGetPredictionImageEndpoint(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.uid = "mocked-uid"
        self.mock_user_id = 42
        self.jpeg_path = f"uploads/predicted/{self.uid}.jpg"
        self.png_path = f"uploads/predicted/{self.uid}.png"

    def tearDown(self):
        app.dependency_overrides = {}

    def override_dependencies(self):
        app.dependency_overrides[get_db] = lambda: MagicMock()
        app.dependency_overrides[get_current_user_id] = lambda: self.mock_user_id

    @patch("controllers.image.query_prediction_image_by_uid", return_value=None)
    def test_prediction_not_found(self, mock_query):
        self.override_dependencies()
        headers = {"Accept": "image/jpeg"}
        response = self.client.get(f"/prediction/{self.uid}/image", headers=headers)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Prediction not found")

  
 
   

    @patch("controllers.image.query_prediction_image_by_uid")
    @patch("os.path.exists", return_value=True)
    def test_unsupported_accept_header(self, mock_exists, mock_query):
        self.override_dependencies()

        mock_session = MagicMock()
        mock_session.predicted_image = self.jpeg_path
        mock_query.return_value = mock_session

        headers = {"Accept": "application/json"}
        response = self.client.get(f"/prediction/{self.uid}/image", headers=headers)

        self.assertEqual(response.status_code, 406)
        self.assertEqual(response.json()["detail"], "Client does not accept an image format")

    @patch("controllers.image.query_prediction_image_by_uid")
    @patch("os.path.exists", return_value=False)
    def test_image_file_missing(self, mock_exists, mock_query):
        self.override_dependencies()

        mock_session = MagicMock()
        mock_session.predicted_image = self.jpeg_path
        mock_query.return_value = mock_session

        headers = {"Accept": "image/jpeg"}
        response = self.client.get(f"/prediction/{self.uid}/image", headers=headers)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Predicted image file not found")
        


    @patch("controllers.image.FileResponse")
    @patch("controllers.image.query_prediction_image_by_uid")
    @patch("os.path.exists", return_value=True)
    def test_valid_jpeg_request(self, mock_exists, mock_query, mock_file_response):
        self.override_dependencies()

        mock_session = MagicMock()
        mock_session.predicted_image = self.jpeg_path
        mock_query.return_value = mock_session

        # Return a real Response with proper headers, not just a MagicMock
        fake_response = Response(content=b"", media_type="image/jpeg")
        mock_file_response.return_value = fake_response

        headers = {"Accept": "image/jpeg"}
        response = self.client.get(f"/prediction/{self.uid}/image", headers=headers)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "image/jpeg")
        
    @patch("controllers.image.FileResponse")
    @patch("controllers.image.query_prediction_image_by_uid")
    @patch("os.path.exists", return_value=True)
    def test_valid_jpg_request(self, mock_exists, mock_query, mock_file_response):
        self.override_dependencies()

        mock_session = MagicMock()
        mock_session.predicted_image = f"uploads/predicted/{self.uid}.jpg"  # explicitly .jpg here
        mock_query.return_value = mock_session

        fake_response = Response(content=b"", media_type="image/jpeg")
        mock_file_response.return_value = fake_response

        headers = {"Accept": "image/jpg"}
        response = self.client.get(f"/prediction/{self.uid}/image", headers=headers)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "image/jpeg")

if __name__ == "__main__":
    unittest.main()
