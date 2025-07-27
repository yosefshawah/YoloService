import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app import app  # Adjust as needed
from database.db import get_db
from dependencies.auth import get_current_user_id

class TestGetPredictionsByLabelEndpoint(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.test_label = "cat"
        self.mock_user_id = 42

    def tearDown(self):
        app.dependency_overrides = {}

    def override_dependencies(self):
        self.mock_db = MagicMock()
        app.dependency_overrides[get_db] = lambda: self.mock_db
        app.dependency_overrides[get_current_user_id] = lambda: self.mock_user_id

    @patch("controllers.prediction.query_sessions_by_label")
    def test_get_predictions_by_label_success(self, mock_query_sessions):
        self.override_dependencies()

        # mock returned sessions
        mock_session1 = MagicMock()
        mock_session1.uid = "uid-123"
        mock_session1.timestamp = "2025-07-27T12:00:00"

        mock_session2 = MagicMock()
        mock_session2.uid = "uid-456"
        mock_session2.timestamp = "2025-07-26T15:30:00"

        mock_query_sessions.return_value = [mock_session1, mock_session2]

        response = self.client.get(f"/predictions/label/{self.test_label}")

        self.assertEqual(response.status_code, 200)
        json_resp = response.json()
        self.assertEqual(len(json_resp), 2)
        self.assertEqual(json_resp[0]["uid"], "uid-123")
        self.assertEqual(json_resp[0]["timestamp"], "2025-07-27T12:00:00")
        self.assertEqual(json_resp[1]["uid"], "uid-456")
        self.assertEqual(json_resp[1]["timestamp"], "2025-07-26T15:30:00")

        # Now use the SAME mock_db instance for asserting call args
        mock_query_sessions.assert_called_once_with(
            self.mock_db, self.test_label, self.mock_user_id
        )

    @patch("controllers.prediction.query_sessions_by_label", return_value=[])
    def test_get_predictions_by_label_no_results(self, mock_query_sessions):
        self.override_dependencies()

        response = self.client.get(f"/predictions/label/{self.test_label}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

if __name__ == "__main__":
    unittest.main()
