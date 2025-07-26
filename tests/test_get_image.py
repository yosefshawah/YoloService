import os
import unittest
from unittest.mock import patch, mock_open
from fastapi.testclient import TestClient
from app import app


class TestGetImageEndpoint(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.test_image_name = "test_image.jpg"
        self.original_path = os.path.join("uploads", "original")
        self.predicted_path = os.path.join("uploads", "predicted")

    @patch("os.path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data=b"dummy image content")
    def test_get_original_image_success(self, mock_file, mock_exists):
        # Mock that the original image file exists
        mock_exists.return_value = True

        response = self.client.get(f"/image/original/{self.test_image_name}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"dummy image content")

        # Assert open called with correct file path
        expected_path = os.path.join(self.original_path, self.test_image_name)
        mock_file.assert_called_with(expected_path, "rb")

    @patch("os.path.exists")
    def test_get_predicted_image_not_found(self, mock_exists):
        # Mock predicted image does not exist
        mock_exists.return_value = False

        response = self.client.get(f"/image/predicted/nonexistent.jpg")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Image not found")

    def test_invalid_type(self):
        response = self.client.get(f"/image/invalidtype/{self.test_image_name}")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Invalid image type")

    # Example placeholder for future DB-related tests using your query helpers:
    # def test_query_sessions_by_label(self):
    #     with patch("path.to.db.session") as mock_db:
    #         mock_db.query.return_value = ... # setup expected mock return
    #         results = query_sessions_by_label(mock_db, "person", user_id=123)
    #         self.assertIsInstance(results, list)
    #         # Add asserts depending on your mocked results


if __name__ == "__main__":
    unittest.main()
