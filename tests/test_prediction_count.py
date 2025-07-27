import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app import app  # adjust import path if needed
from database.db import get_db

class TestGetPredictionCountLastWeek(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.mock_db = MagicMock()
        app.dependency_overrides[get_db] = lambda: self.mock_db

    def tearDown(self):
        app.dependency_overrides = {}

    @patch("controllers.stats.query_prediction_count_last_week")
    def test_get_prediction_count_success(self, mock_query_count):
        mock_query_count.return_value = 5  # example count

        response = self.client.get("/predictions/count")
        self.assertEqual(response.status_code, 200)
        json_resp = response.json()
        self.assertIn("count", json_resp)
        self.assertEqual(json_resp["count"], 5)

        # Assert query called with the mock db session
        mock_query_count.assert_called_once_with(self.mock_db)

if __name__ == "__main__":
    unittest.main()
