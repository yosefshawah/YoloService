import os
import uuid
from typing import Dict, List, Tuple, Any

from PIL import Image
from ultralytics import YOLO


class YoloPredictor:
    """Encapsulates YOLO inference and artifact handling.

    The class lazily loads the model once and provides a simple API to run
    predictions on a given local image path, saving the annotated output to
    a specified destination path.
    """

    def __init__(self, model_path: str = "yolov8n.pt") -> None:
        # Force CPU to ensure compatibility in constrained environments
        import torch  # local import to avoid global side-effects

        torch.cuda.is_available = lambda: False
        self.model = YOLO(model_path)

    def predict_to_file(self, original_path: str, predicted_path: str) -> Tuple[List[Dict[str, Any]], int]:
        results = self.model(original_path, device="cpu")
        annotated_frame = results[0].plot()
        annotated_image = Image.fromarray(annotated_frame)
        os.makedirs(os.path.dirname(predicted_path), exist_ok=True)
        annotated_image.save(predicted_path)

        detections: List[Dict[str, Any]] = []
        for box in results[0].boxes:
            label_idx = int(box.cls[0].item())
            label = self.model.names[label_idx]
            score = float(box.conf[0])
            bbox = box.xyxy[0].tolist()
            detections.append({
                "label": label,
                "score": score,
                "box": bbox,
            })

        return detections, len(results[0].boxes)


