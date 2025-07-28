import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app import app  
from dependencies.auth import get_current_user_id

TEST_USER_ID = 123

class TestStatsEndpoint(unittest.TestCase):
    def setUp(self):
        app.dependency_overrides[get_current_user_id] = lambda: TEST_USER_ID
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides = {}

    @patch("controllers.stats.query_total_predictions_last_8_days")
    @patch("controllers.stats.query_detection_objects_last_8_days")
    def test_stats_returns_only_current_user_data(
        self,
        mock_query_detections,
        mock_query_total
    ):
        mock_query_total.return_value = 2
        mock_query_detections.return_value = [
            type("Row", (), {"label": "cat", "score": 0.8}),
            type("Row", (), {"label": "dog", "score": 0.9}),
        ]

        response = self.client.get("/stats")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["total_predictions"], 2)
        self.assertAlmostEqual(data["average_confidence_score"], 0.85)
        self.assertEqual(data["most_common_labels"], {"cat": 1, "dog": 1})

if __name__ == "__main__":
    unittest.main()
