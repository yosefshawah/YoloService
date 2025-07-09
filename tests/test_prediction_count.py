from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_prediction_count_format():
    response = client.get("/prediction/count")
    assert response.status_code == 200
    data = response.json()
    assert "count" in data
    assert isinstance(data["count"], int)
    assert data["count"] >= 0

