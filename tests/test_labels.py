import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app import app

class TestLabelsEndpoint(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    @patch("controllers.labels.query_unique_labels_last_week")
    def test_labels_endpoint(self, mock_query):
        # Arrange
        mock_query.return_value = ["cat", "dog"]

        # Act
        response = self.client.get("/labels")
        
        # Assert
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIsInstance(data, dict)
        self.assertIn("labels", data)

        labels = data["labels"]
        self.assertIsInstance(labels, list)

        for label in labels:
            self.assertIsInstance(label, str)
            self.assertTrue(label.strip(), "Label should not be empty")

        self.assertEqual(len(labels), len(set(labels)), "Duplicate labels found")
        self.assertCountEqual(labels, ["cat", "dog"])
