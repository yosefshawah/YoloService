import unittest
from unittest.mock import patch, mock_open, MagicMock
from fastapi.testclient import TestClient
from app import app
import sys
import os



class TestImageEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.image_data = b"fake image data"
        self.uid = "abc123"
        self.image_filename = "abc123.jpg"
        self.image_path = f"uploads/original/{self.image_filename}"
        self.predicted_image_path = f"uploads/predicted/{self.image_filename}"

    @patch("controllers.image.os.path.exists", return_value=True)
    @patch("controllers.image.FileResponse")
    def test_get_image_by_type_success(self, mock_file_response, mock_exists):
        print(f"\n=== Testing get_image_by_type_success ===")
        
        # Mock FileResponse to return our expected response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = self.image_data
        mock_file_response.return_value = mock_response
        
        response = self.client.get(f"/image/original/{self.image_filename}")
        
        print(f"Response status: {response.status_code}")
        print(f"os.path.exists called with: {mock_exists.call_args_list}")
        print(f"FileResponse called with: {mock_file_response.call_args_list}")
        
        if response.status_code != 200:
            print(f"Response text: {response.text}")
        
        # Verify the path was constructed correctly
        expected_path = os.path.join("uploads", "original", self.image_filename)
        mock_exists.assert_called_with(expected_path)
        mock_file_response.assert_called_with(expected_path)
        
        self.assertEqual(response.status_code, 200)

    @patch("controllers.image.os.path.exists", return_value=True)
    @patch("controllers.image.query_prediction_image_by_uid")
    @patch("controllers.image.FileResponse")
    def test_get_prediction_image_success(self, mock_file_response, mock_query, mock_exists):
        print(f"\n=== Testing get_prediction_image_success ===")
        
        # Setup the database mock
        mock_session = MagicMock()
        mock_session.predicted_image = self.predicted_image_path
        mock_query.return_value = mock_session
        
        # Mock FileResponse
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = self.image_data
        mock_file_response.return_value = mock_response
        
        headers = {"accept": "image/jpeg"}
        response = self.client.get(f"/prediction/{self.uid}/image", headers=headers)
        
        print(f"Request URL: /prediction/{self.uid}/image")
        print(f"Request headers: {headers}")
        print(f"Response status: {response.status_code}")
        print(f"mock_query called: {mock_query.called}")
        print(f"mock_query call_args: {mock_query.call_args}")
        print(f"os.path.exists called with: {mock_exists.call_args_list}")
        
        if response.status_code != 200:
            print(f"Response text: {response.text}")
        
        # Verify the query was called correctly
        mock_query.assert_called_once()
        # Verify file existence was checked
        mock_exists.assert_called_with(self.predicted_image_path)
        # Verify FileResponse was called with correct media type
        mock_file_response.assert_called_with(self.predicted_image_path, media_type="image/jpeg")
        
        self.assertEqual(response.status_code, 200)

    @patch("controllers.image.os.path.exists", return_value=False)
    def test_get_image_file_not_found(self, mock_exists):
        response = self.client.get(f"/image/original/{self.image_filename}")
        self.assertEqual(response.status_code, 404)

    @patch("controllers.image.os.path.exists", return_value=True)
    def test_get_image_invalid_type(self, mock_exists):
        response = self.client.get(f"/image/invalid_type/{self.image_filename}")
        self.assertEqual(response.status_code, 400)

    @patch("controllers.image.query_prediction_image_by_uid", return_value=None)
    def test_prediction_uid_not_found(self, mock_query):
        headers = {"accept": "image/jpeg"}
        response = self.client.get(f"/prediction/{self.uid}/image", headers=headers)
        self.assertEqual(response.status_code, 404)

    @patch("controllers.image.os.path.exists", return_value=True)
    @patch("controllers.image.query_prediction_image_by_uid")
    def test_prediction_unsupported_accept_header(self, mock_query, mock_exists):
        print(f"\n=== Testing prediction_unsupported_accept_header ===")
        
        mock_session = MagicMock()
        mock_session.predicted_image = self.predicted_image_path
        mock_query.return_value = mock_session
        
        headers = {"accept": "text/html"}
        response = self.client.get(f"/prediction/{self.uid}/image", headers=headers)
        
        print(f"Request headers: {headers}")
        print(f"Response status: {response.status_code}")
        print(f"Expected status: 406")
        print(f"Response text: {response.text}")
        print(f"mock_query called: {mock_query.called}")
        print(f"mock_query call_args: {mock_query.call_args}")
        
        self.assertEqual(response.status_code, 406)

    # Additional test for PNG accept header
    @patch("controllers.image.os.path.exists", return_value=True)
    @patch("controllers.image.query_prediction_image_by_uid")
    @patch("controllers.image.FileResponse")
    def test_get_prediction_image_png_success(self, mock_file_response, mock_query, mock_exists):
        mock_session = MagicMock()
        mock_session.predicted_image = self.predicted_image_path
        mock_query.return_value = mock_session
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_file_response.return_value = mock_response
        
        headers = {"accept": "image/png"}
        response = self.client.get(f"/prediction/{self.uid}/image", headers=headers)
        
        self.assertEqual(response.status_code, 200)
        mock_file_response.assert_called_with(self.predicted_image_path, media_type="image/png")

    @patch("controllers.image.os.path.exists", return_value=True)
    @patch("controllers.image.query_prediction_image_by_uid")
    def test_prediction_image_file_not_found(self, mock_query, mock_exists):
        # Mock the database query to return a session, but file doesn't exist
        mock_session = MagicMock()
        mock_session.predicted_image = self.predicted_image_path
        mock_query.return_value = mock_session
        
        # Override the exists mock to return False for the image file
        mock_exists.return_value = False
        
        headers = {"accept": "image/jpeg"}
        response = self.client.get(f"/prediction/{self.uid}/image", headers=headers)
        
        self.assertEqual(response.status_code, 404)

if __name__ == "__main__":
    unittest.main(verbosity=2)