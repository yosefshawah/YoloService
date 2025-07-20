import unittest
from fastapi.testclient import TestClient
from app import app  # adjust import according to your project structure

class TestHealthEndpoint(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health_status_ok(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

if __name__ == "__main__":
    unittest.main()
