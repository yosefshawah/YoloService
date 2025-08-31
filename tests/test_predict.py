import os
import time
import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import UploadFile
from app import app  # Adjust import if needed
from database.db import get_db
from dependencies.auth import get_current_user_id

class TestPredictEndpoint(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.mock_user_id = 42
        self.mock_file = MagicMock(spec=UploadFile)
        self.mock_file.filename = "test.jpg"
        self.mock_file.file = MagicMock()

    def tearDown(self):
        app.dependency_overrides = {}

    def override_dependencies(self):
        app.dependency_overrides[get_db] = lambda: MagicMock()
        app.dependency_overrides[get_current_user_id] = lambda: self.mock_user_id

    @patch("controllers.prediction.save_detection_object")
    @patch("controllers.prediction.save_prediction_session")
    @patch("controllers.prediction.model")
    @patch("shutil.copyfileobj")
    @patch("controllers.prediction.Image.fromarray")
    @patch("controllers.prediction.upload_path_to_s3_key")
    @patch("controllers.prediction.get_s3_client", return_value=None)
    @patch("controllers.prediction.s3_client", new=None)
    def test_predict_success(self, mock_get_s3, mock_s3_upload, mock_fromarray, mock_copyfileobj, mock_model, mock_save_session, mock_save_detection):
        self.override_dependencies()

        # Setup mock model return value
        box1 = MagicMock()
        box1.cls = [MagicMock()]
        box1.cls[0].item.return_value = 0
        box1.conf = [0.95]
        mock_array1 = MagicMock()
        mock_array1.tolist.return_value = [10, 20, 30, 40]
        box1.xyxy = [mock_array1]

        box2 = MagicMock()
        box2.cls = [MagicMock()]
        box2.cls[0].item.return_value = 1
        box2.conf = [0.85]
        mock_array2 = MagicMock()
        mock_array2.tolist.return_value = [50, 60, 70, 80]
        box2.xyxy = [mock_array2]

        mock_result = MagicMock()
        mock_result.plot.return_value = b"fake image bytes"
        mock_result.boxes = [box1, box2]

        mock_model.return_value = [mock_result]

        # Mock PIL.Image.fromarray to avoid real image handling
        mock_img_instance = MagicMock()
        mock_fromarray.return_value = mock_img_instance

        response = self.client.post(
            "/predict",
            files={"file": ("test.jpg", b"fake image content", "image/jpeg")},
            headers={"accept": "application/json"},
        )

        self.assertEqual(response.status_code, 200)
        json_resp = response.json()
        self.assertEqual(json_resp["detection_count"], 2)
        self.assertIn("labels", json_resp)
        self.assertIsInstance(json_resp["time_took"], float)

        # Confirm save functions called
        mock_save_session.assert_called_once()
        self.assertEqual(mock_save_detection.call_count, 2)

if __name__ == "__main__":
    unittest.main()
