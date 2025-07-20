from fastapi import Depends, FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import FileResponse, Response
from ultralytics import YOLO
from PIL import Image
import sqlite3
import os
import uuid
import shutil
import time
from fastapi import Request
from dependencies.auth import get_current_user_id
# Disable GPU usage
import torch

torch.cuda.is_available = lambda: False

app = FastAPI()


UPLOAD_DIR = "uploads/original"
PREDICTED_DIR = "uploads/predicted"
DB_PATH = "predictions.db"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(PREDICTED_DIR, exist_ok=True)

# Download the AI model (tiny model ~6MB)
model = YOLO("yolov8n.pt")


# Initialize SQLite
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        # Create the predictions main table to store the prediction session
        conn.execute(
            """
                CREATE TABLE IF NOT EXISTS prediction_sessions (
                    uid TEXT PRIMARY KEY,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    original_image TEXT,
                    predicted_image TEXT,
                    user_id INTEGER,
                    FOREIGN KEY (user_id) REFERENCES users(id));
            """
        )

        # Create the objects table to store individual detected objects in a given image
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS detection_objects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prediction_uid TEXT,
                label TEXT,
                score REAL,
                box TEXT,
                FOREIGN KEY (prediction_uid) REFERENCES prediction_sessions (uid)
            )
        """
        )

        conn.execute(
            """
                    CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL);
                    """
        )

        # Create index for faster queries
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_prediction_uid ON detection_objects (prediction_uid)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_label ON detection_objects (label)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_score ON detection_objects (score)"
        )


init_db()


def save_prediction_session(uid, original_image, predicted_image, user_id):
    """
    Save prediction session to database
    """
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO prediction_sessions (uid, original_image, predicted_image, user_id)
            VALUES (?, ?, ?, ?)
            """,
            (uid, original_image, predicted_image, user_id),
        )


def save_detection_object(prediction_uid, label, score, box):
    """
    Save detection object to database
    """
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO detection_objects (prediction_uid, label, score, box)
            VALUES (?, ?, ?, ?)
        """,
            (prediction_uid, label, score, str(box)),
        )


@app.post("/predict")
def predict(user_id = Depends(get_current_user_id) ,file: UploadFile = File(...)):
    """
    Predict objects in an image
    """
    
    
    start_time = time.time()
    ext = os.path.splitext(file.filename)[1]
    uid = str(uuid.uuid4())
    original_path = os.path.join(UPLOAD_DIR, uid + ext)
    predicted_path = os.path.join(PREDICTED_DIR, uid + ext)

    with open(original_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

    results = model(original_path, device="cpu")

    annotated_frame = results[0].plot()  # NumPy image with boxes
    annotated_image = Image.fromarray(annotated_frame)
    annotated_image.save(predicted_path)

    save_prediction_session(uid, original_path, predicted_path, user_id=user_id)

    detected_labels = []
    for box in results[0].boxes:
        label_idx = int(box.cls[0].item())
        label = model.names[label_idx]
        score = float(box.conf[0])
        bbox = box.xyxy[0].tolist()
        save_detection_object(uid, label, score, bbox)
        detected_labels.append(label)

    processing_time = round(time.time() - start_time, 2)

    return {
        "prediction_uid": uid,
        "detection_count": len(results[0].boxes),
        "labels": detected_labels,
        "time_took": processing_time,
    }



@app.get("/prediction/{uid}")
def get_prediction_by_uid(  uid: str, user_id = Depends(get_current_user_id)):
 

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        # Only fetch if it belongs to this user
        session = conn.execute(
            "SELECT * FROM prediction_sessions WHERE uid = ? AND user_id = ?",
            (uid, user_id)
        ).fetchone()

        if not session:
            raise HTTPException(status_code=401, detail="Unauthorized or prediction not found")

        objects = conn.execute(
            "SELECT * FROM detection_objects WHERE prediction_uid = ?",
            (uid,)
        ).fetchall()

        return {
            "uid": session["uid"],
            "timestamp": session["timestamp"],
            "original_image": session["original_image"],
            "predicted_image": session["predicted_image"],
            "detection_objects": [
                {
                    "id": obj["id"],
                    "label": obj["label"],
                    "score": obj["score"],
                    "box": obj["box"],
                }
                for obj in objects
            ],
        }


@app.get("/predictions/label/{label}")
def get_predictions_by_label(label: str, user_id: int = Depends(get_current_user_id)):
    """
    Get prediction sessions belonging to the current user
    that contain objects with the specified label.
    """
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT DISTINCT ps.uid, ps.timestamp
            FROM prediction_sessions ps
            JOIN detection_objects do ON ps.uid = do.prediction_uid
            WHERE do.label = ? AND ps.user_id = ?
            """,
            (label, user_id),
        ).fetchall()

        return [{"uid": row["uid"], "timestamp": row["timestamp"]} for row in rows]


@app.get("/predictions/score/{min_score}")
def get_predictions_by_score(min_score: float, user_id: int = Depends(get_current_user_id)):
    """
    Get prediction sessions belonging to the current user
    that contain objects with score >= min_score.
    """
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT DISTINCT ps.uid, ps.timestamp
            FROM prediction_sessions ps
            JOIN detection_objects do ON ps.uid = do.prediction_uid
            WHERE do.score >= ? AND ps.user_id = ?
            """,
            (min_score, user_id),
        ).fetchall()

        return [{"uid": row["uid"], "timestamp": row["timestamp"]} for row in rows]


@app.get("/image/{type}/{filename}")
def get_image(type: str, filename: str):
    """
    Get image by type and filename
    """
    if type not in ["original", "predicted"]:
        raise HTTPException(status_code=400, detail="Invalid image type")
    path = os.path.join("uploads", type, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(path)


@app.get("/prediction/{uid}/image")
def get_prediction_image(uid: str, request: Request):
    """
    Get prediction image by uid
    """
    accept = request.headers.get("accept", "")
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT predicted_image FROM prediction_sessions WHERE uid = ?", (uid,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Prediction not found")
        image_path = row[0]

    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="Predicted image file not found")

    if "image/png" in accept:
        return FileResponse(image_path, media_type="image/png")
    elif "image/jpeg" in accept or "image/jpg" in accept:
        return FileResponse(image_path, media_type="image/jpeg")
    else:
        # If the client doesn't accept image, respond with 406 Not Acceptable
        raise HTTPException(
            status_code=406, detail="Client does not accept an image format"
        )


@app.get("/predictions/count")
def get_prediction_count_last_week():
    """
    Get the number of predictions made in the last 7 days
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            """
            SELECT COUNT(*) FROM prediction_sessions
            WHERE timestamp >= datetime('now', '-7 days')
        """
        )
        count = cursor.fetchone()[0]
    return {"count": count}


@app.get("/labels")
def get_unique_labels_last_week():
    """
    Get all unique object labels detected in the last 7 days
    """
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            """
            SELECT DISTINCT do.label
            FROM detection_objects do
            JOIN prediction_sessions ps ON do.prediction_uid = ps.uid
            WHERE ps.timestamp >= datetime('now', '-7 days')
        """
        )
        labels = [row["label"] for row in cursor.fetchall()]
    return {"labels": labels}


import os
from fastapi import HTTPException


@app.delete("/prediction/{uid}")
def delete_prediction(uid: str, user_id: int = Depends(get_current_user_id)):
    with sqlite3.connect(DB_PATH) as conn:
        # Check that the prediction exists and belongs to the current user
        row = conn.execute(
            """
            SELECT original_image, predicted_image 
            FROM prediction_sessions 
            WHERE uid = ? AND user_id = ?
            """,
            (uid, user_id),
        ).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Prediction not found or access denied")

        original_path, predicted_path = row

        # Delete records from related tables
        conn.execute("DELETE FROM detection_objects WHERE prediction_uid = ?", (uid,))
        conn.execute("DELETE FROM prediction_sessions WHERE uid = ?", (uid,))
        conn.commit()

    # Delete image files from disk
    for path in [original_path, predicted_path]:
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except Exception as e:
                print(f"Failed to delete file {path}: {e}")

    return {"detail": f"Prediction {uid} and associated files deleted"}



from collections import Counter
from fastapi import APIRouter
import sqlite3


@app.get("/stats")
def get_prediction_statistics_last_week(user_id: int = Depends(get_current_user_id)):
    """
    Get stats about predictions in the last 8 days for the authenticated user:
    - Total predictions
    - Average confidence score
    - Most common labels
    """
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        # Get total predictions in last 8 days for this user
        total = conn.execute(
            """
            SELECT COUNT(*) as count
            FROM prediction_sessions
            WHERE user_id = ? AND timestamp >= datetime('now', '-8 days')
            """,
            (user_id,),
        ).fetchone()["count"]

        # Get all scores and labels in last 8 days for this user
        rows = conn.execute(
            """
            SELECT do.label, do.score
            FROM detection_objects do
            JOIN prediction_sessions ps ON do.prediction_uid = ps.uid
            WHERE ps.user_id = ? AND ps.timestamp >= datetime('now', '-8 days')
            """,
            (user_id,),
        ).fetchall()

        scores = [row["score"] for row in rows]
        labels = [row["label"] for row in rows]

        avg_score = round(sum(scores) / len(scores), 4) if scores else 0.0
        label_counts = dict(Counter(labels))

    return {
        "total_predictions": total,
        "average_confidence_score": avg_score,
        "most_common_labels": label_counts,
    }


@app.get("/health")
def health():
    """
    Health check endpoint
    """
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
