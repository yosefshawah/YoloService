from locust import HttpUser, task, between
import os
import random
import string
from requests.auth import HTTPBasicAuth


def random_username() -> str:
    return "user_" + "".join(random.choice(string.ascii_lowercase) for _ in range(6))


def get_auth():
    username = os.getenv("LOADTEST_USER")
    password = os.getenv("LOADTEST_PASS")
    if username and password:
        return HTTPBasicAuth(username, password)
    # fall back to anonymous (service will auto-create anonymous)
    return None


class YoloServiceUser(HttpUser):
    wait_time = between(0.5, 1.5)

    def on_start(self):
        self.auth = get_auth()
        # Preload a small image from repo for uploads
        self.sample_image_path = os.getenv("LOADTEST_IMAGE", "beatles.jpeg")
        if not os.path.exists(self.sample_image_path):
            # try fallback
            self.sample_image_path = "dog.png"

    @task(2)
    def health(self):
        self.client.get("/health")

    @task(6)
    def predict_upload_and_fetch(self):
        # Upload image to /predict
        files = None
        try:
            files = {"file": (os.path.basename(self.sample_image_path), open(self.sample_image_path, "rb"), "image/jpeg")}
        except Exception:
            return
        headers = {"accept": "application/json"}
        params = {}
        auth = self.auth
        with self.client.post("/predict", files=files, headers=headers, params=params, auth=auth, catch_response=True) as resp:
            if resp.status_code != 200:
                resp.failure(f"predict failed: {resp.status_code}")
                return
            data = resp.json()
            uid = data.get("prediction_uid")
            if not uid:
                resp.failure("missing uid in predict response")
                return
        # Fetch by uid
        self.client.get(f"/prediction/{uid}", auth=auth)
        # Query by one of the labels if present
        labels = data.get("labels") if 'data' in locals() else None
        if labels:
            self.client.get(f"/predictions/label/{labels[0]}", auth=auth)
        # Optionally delete to keep storage small
        if os.getenv("LOADTEST_DELETE", "true").lower() == "true":
            self.client.delete(f"/prediction/{uid}", auth=auth)

    @task(2)
    def predict_via_s3_key_if_configured(self):
        s3_key = os.getenv("LOADTEST_S3_KEY")
        if not s3_key:
            return
        params = {"img": s3_key}
        auth = self.auth
        with self.client.post("/predict", params=params, auth=auth, catch_response=True) as resp:
            if resp.status_code != 200:
                resp.failure(f"predict S3 failed: {resp.status_code}")
                return
            uid = resp.json().get("prediction_uid")
            if uid:
                self.client.get(f"/prediction/{uid}", auth=auth)
                if os.getenv("LOADTEST_DELETE", "true").lower() == "true":
                    self.client.delete(f"/prediction/{uid}", auth=auth)
