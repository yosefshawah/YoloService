# YOLO Object Detection Service

This is a FastAPI-based web service that performs object detection on uploaded images using the YOLOv8 model. The application analyzes images, detects objects, and stores prediction results in a SQLite database for later retrieval.

## Setup Instructions

1. Create a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate
```

2. Install requirements:
```bash
pip install -r torch-requirements.txt
pip install -r requirements.txt
```

3. Run the application:
```bash
python app.py
```

The service will be available at http://localhost:8080

## API Endpoints

* `POST /predict` - Upload an image for object detection
* `GET /prediction/{uid}` - Get details of a specific prediction by ID
* `GET /predictions/label/{label}` - Get all predictions containing a specific object label (e.g., "person", "car")
* `GET /predictions/score/{min_score}` - Get predictions with confidence score above threshold (e.g., 0.5)
* `GET /prediction/{uid}/image` - Get the processed image with detection boxes
* `GET /image/{type}/{filename}` - Get original or predicted image by filename

## Testing the API

You can use tools like curl, Postman, or a web browser to test the endpoints. For example:

1. Upload an image:
```bash
curl -X POST -F "file=@your_image.jpg" http://localhost:8080/predict
```

2. View detection results (replace {uid} with the ID returned from the upload):
```bash
curl http://localhost:8080/prediction/{uid} 