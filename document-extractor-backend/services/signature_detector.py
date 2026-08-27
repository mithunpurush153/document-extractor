"""
Signature detection service.
loads the local YOLOv8 signature detector (best.pt) via ultralytics
and runs CPU inference.

"""
import logging

from PIL import Image
from ultralytics import YOLO

from config import SIGNATURE_CONFIDENCE_THRESHOLD, SIGNATURE_MODEL_PATH

logger = logging.getLogger(__name__)

_model = None


def get_signature_model():
    """
    Loads the local YOLOv8 signature detector once, reused across
    every request.
    """
    global _model
    if _model is None:
        logger.info("Loading signature detection model from %s (CPU)", SIGNATURE_MODEL_PATH)
        _model = YOLO(SIGNATURE_MODEL_PATH)
        logger.info("Signature detection model ready.")
    return _model


def detect_signatures(image: Image.Image) -> list:
    model = get_signature_model()
    results = model.predict(
        source=image,
        conf=SIGNATURE_CONFIDENCE_THRESHOLD,
        device="cpu",
        verbose=False,
    )

    detections = []
    for result in results:
        for box in result.boxes:
            confidence = float(box.conf[0])
            x1, y1, x2, y2 = [float(v) for v in box.xyxy[0].tolist()]
            detections.append({"confidence": confidence, "box": [x1, y1, x2, y2]})

    return detections
