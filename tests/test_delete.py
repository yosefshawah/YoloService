import os
import unittest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from app import app
from database.db import get_db
from dependencies.auth import get_current_user_id
from models.models import PredictionSession



class TestDeletePredictionEndpoint(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.uid = "test-uid"
        self.user_id = 123
        self.original_path = "uploads/original/test.jpg"
        self.predicted_path = "uploads/predicted/test.jpg"

        # Create a mock prediction object
        self.mock_prediction = MagicMock(spec=PredictionSession)
        self.mock_prediction.uid = self.uid
        self.mock_prediction.user_id = self.user_id
        self.mock_prediction.original_image = self.original_path
        self.mock_prediction.predicted_image = self.predicted_path
        self.mock_prediction.uid = 1  # for DetectionObject deletion filter

        # Create a mock DB session
        self.mock_db = MagicMock()
        # When filter_by is called, return an object whose first() returns the mock prediction
        filter_by_mock = MagicMock()
        filter_by_mock.first.return_value = self.mock_prediction
        self.mock_db.query.return_value.filter_by = MagicMock(return_value=filter_by_mock)
        # Mock filter().delete() to do nothing
        self.mock_db.query.return_value.filter.return_value.delete.return_value = None

        # Override get_db dependency to return the mock DB session
        def override_get_db():
            yield self.mock_db
        app.dependency_overrides = {}
        app.dependency_overrides[get_db] = override_get_db

        # Override get_current_user_id dependency to return the mock user_id
        async def override_get_current_user_id():
            return self.user_id
        app.dependency_overrides[get_current_user_id] = override_get_current_user_id

    @patch("os.path.exists", return_value=True)
    @patch("os.remove")
    def test_delete_prediction_success(self, mock_remove, mock_exists):
        response = self.client.delete(f"/prediction/{self.uid}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"message": "Prediction deleted successfully"})

        # Confirm the files were attempted to be deleted
        mock_remove.assert_any_call(self.original_path)
        mock_remove.assert_any_call(self.predicted_path)

        # Confirm the db delete and commit were called
        self.mock_db.delete.assert_called_once_with(self.mock_prediction)
        self.mock_db.commit.assert_called_once()
        

    def test_delete_prediction_not_found(self):
        # Override mock so that filter_by.first() returns None (prediction not found)
        filter_by_mock = MagicMock()
        filter_by_mock.first.return_value = None
        self.mock_db.query.return_value.filter_by = MagicMock(return_value=filter_by_mock)

        response = self.client.delete(f"/prediction/{self.uid}")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "Prediction not found"})

if __name__ == "__main__":
    unittest.main()
