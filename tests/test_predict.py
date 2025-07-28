import os
import time
import uuid
import shutil
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
    @patch("uuid.uuid4", return_value=uuid.UUID("12345678-1234-5678-1234-567812345678"))
    def test_predict_success(self, mock_uuid, mock_copyfileobj, mock_model, mock_save_session, mock_save_detection):
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

        # Also mock PIL.Image.fromarray and save to avoid actual file I/O
        with patch("controllers.prediction.Image.fromarray") as mock_fromarray:
            mock_img_instance = MagicMock()
            mock_fromarray.return_value = mock_img_instance

            response = self.client.post(
                "/predict",
                files={"file": ("test.jpg", b"fake image content", "image/jpeg")},
                headers={"accept": "application/json"},
            )

            self.assertEqual(response.status_code, 200)
            json_resp = response.json()
            self.assertEqual(json_resp["prediction_uid"], "12345678-1234-5678-1234-567812345678")
            self.assertEqual(json_resp["detection_count"], 2)
            self.assertIn("labels", json_resp)
            self.assertIsInstance(json_resp["time_took"], float)

            # Check detected labels use model.names mock - we can patch model.names too if needed
            # But for now just check label list exists
            self.assertTrue(len(json_resp["labels"]) == 2)

            # Confirm save functions called
            mock_save_session.assert_called_once()
            self.assertEqual(mock_save_detection.call_count, 2)

if __name__ == "__main__":
    unittest.main()
