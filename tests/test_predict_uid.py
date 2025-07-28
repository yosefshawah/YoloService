import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app import app  # Adjust import if your FastAPI app is elsewhere
from database.db import get_db
from dependencies.auth import get_current_user_id

class TestGetPredictionByUid(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.mock_uid = "mocked-uid"
        self.mock_user_id = 42

    def tearDown(self):
        app.dependency_overrides = {}

    def override_dependencies(self):
        # Mock get_db dependency with MagicMock
        app.dependency_overrides[get_db] = lambda: MagicMock()
        # Mock current user id dependency
        app.dependency_overrides[get_current_user_id] = lambda: self.mock_user_id

    @patch("controllers.prediction.get_prediction_session")
    @patch("controllers.prediction.get_detection_objects")
    def test_successful_prediction_response(self, mock_get_detection_objects, mock_get_prediction_session):
        self.override_dependencies()

        # Mock the prediction session return value
        mock_session = MagicMock()
        mock_session.uid = self.mock_uid
        mock_session.timestamp = "2025-07-27T12:00:00"
        mock_session.original_image = "uploads/original/mocked-uid.png"
        mock_session.predicted_image = "uploads/predicted/mocked-uid.png"
        mock_get_prediction_session.return_value = mock_session

        # Mock detection objects returned
        mock_obj1 = MagicMock(id=1, label="cat", score=0.9, box=[10, 20, 30, 40])
        mock_obj2 = MagicMock(id=2, label="dog", score=0.8, box=[50, 60, 70, 80])
        mock_get_detection_objects.return_value = [mock_obj1, mock_obj2]

        response = self.client.get(f"/prediction/{self.mock_uid}")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["uid"], self.mock_uid)
        self.assertEqual(data["timestamp"], "2025-07-27T12:00:00")
        self.assertEqual(data["original_image"], "uploads/original/mocked-uid.png")
        self.assertEqual(data["predicted_image"], "uploads/predicted/mocked-uid.png")
        self.assertEqual(len(data["detection_objects"]), 2)
        self.assertEqual(data["detection_objects"][0]["label"], "cat")
        self.assertEqual(data["detection_objects"][1]["label"], "dog")

    @patch("controllers.prediction.get_prediction_session", return_value=None)
    def test_prediction_not_found(self, mock_get_prediction_session):
        self.override_dependencies()

        response = self.client.get(f"/prediction/{self.mock_uid}")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Unauthorized or prediction not found")


if __name__ == "__main__":
    unittest.main()
