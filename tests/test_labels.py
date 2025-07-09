import unittest
from fastapi.testclient import TestClient
from app import app
from PIL import Image
import io
import time

class TestLabelsEndpoint(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

        # Upload a sample image to ensure there is at least one prediction with labels
        test_image = Image.new('RGB', (100, 100), color='blue')
        image_bytes = io.BytesIO()
        test_image.save(image_bytes, format='JPEG')
        image_bytes.seek(0)

        response = self.client.post(
            "/predict",
            files={"file": ("test.jpg", image_bytes, "image/jpeg")}
        )
        self.assertEqual(response.status_code, 200)
        self.prediction_data = response.json()
        time.sleep(1)  # Ensure timestamp is properly recorded

def test_labels_endpoint(self):
    """Test that /labels returns correct label list structure and values"""
    response = self.client.get("/labels")
    self.assertEqual(response.status_code, 200)

    data = response.json()
    
    # Expect a dict with 'labels' key containing list of labels
    self.assertIsInstance(data, dict)
    self.assertIn("labels", data)
    labels_list = data["labels"]
    self.assertIsInstance(labels_list, list)

    # Check all labels are strings and non-empty
    for label in labels_list:
        self.assertIsInstance(label, str)
        self.assertTrue(label.strip(), "Label should not be empty")

    # Check there are no duplicates
    self.assertEqual(len(labels_list), len(set(labels_list)), "Duplicate labels found")

    # (Optional) Check known label exists if predict succeeded
    if "labels" in self.prediction_data:
        for expected_label in self.prediction_data["labels"]:
            self.assertIn(expected_label, labels_list)
