import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app import app
from dependencies.auth import get_current_user_id

TEST_USER_ID = 2001
SECOND_USER_ID = 2002


class TestGetPredictionsByScore(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides = {}

    @patch("controllers.stats.query_sessions_by_min_score")
    def test_get_predictions_above_threshold(self, mock_query):
        app.dependency_overrides[get_current_user_id] = lambda: TEST_USER_ID

        # Mock a fake SQLAlchemy model object with uid/timestamp
        mock_query.return_value = [
            type("Session", (), {"uid": "uid_high_score", "timestamp": "2024-01-01T00:00:00"})
        ]

        response = self.client.get("/predictions/score/0.9")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["uid"], "uid_high_score")

    @patch("controllers.stats.query_sessions_by_min_score")
    def test_get_predictions_none_match(self, mock_query):
        app.dependency_overrides[get_current_user_id] = lambda: TEST_USER_ID

        mock_query.return_value = []

        response = self.client.get("/predictions/score/0.99")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    @patch("controllers.stats.query_sessions_by_min_score")
    def test_predictions_filtered_by_user(self, mock_query):
        app.dependency_overrides[get_current_user_id] = lambda: SECOND_USER_ID

        mock_query.return_value = [
            type("Session", (), {"uid": "uid_for_second_user", "timestamp": "2024-01-02T00:00:00"})
        ]

        response = self.client.get("/predictions/score/0.9")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["uid"], "uid_for_second_user")


if __name__ == "__main__":
    unittest.main()
