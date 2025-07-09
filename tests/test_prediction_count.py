import unittest
from fastapi.testclient import TestClient
from app import app

class TestPredictionCount(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_prediction_count_format(self):
        response = self.client.get("/predictions/count")
       # self.assertEqual(response.status_code, 200)
        print(response)
        data = response.json()
        self.assertIn("count", data)
        self.assertIsInstance(data["count"], int)
        self.assertGreaterEqual(data["count"], 0)
