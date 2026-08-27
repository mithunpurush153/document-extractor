"""
Stamp detection service.

"""
import logging

import torch
from PIL import Image
from transformers import AutoImageProcessor, AutoModelForObjectDetection

from config import STAMP_CONFIDENCE_THRESHOLD, STAMP_MODEL_DIR, STAMP_OVERLAP_THRESHOLD

logger = logging.getLogger(__name__)

_processor = None
_model = None


def get_stamp_model():
    """
    Loads the Ooredoo stamp detector from local files once, reused
    across every request. 
    """
    global _processor, _model
    if _model is None:
        logger.info("Loading stamp detection model from %s (CPU, local files only)", STAMP_MODEL_DIR)
        _processor = AutoImageProcessor.from_pretrained(STAMP_MODEL_DIR, local_files_only=True)
        _model = AutoModelForObjectDetection.from_pretrained(STAMP_MODEL_DIR, local_files_only=True)
        _model.eval()
        logger.info("Stamp detection model ready.")
    return _processor, _model


def _box_area(box: list) -> float:
    width = max(0, box[2] - box[0])
    height = max(0, box[3] - box[1])
    return width * height


def _calculate_overlap(box1: list, box2: list) -> float:
    """Fraction of the SMALLER box's area covered by the intersection. Unchanged from stamp_test.py."""
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])

    width = max(0, x2 - x1)
    height = max(0, y2 - y1)
    intersection = width * height
    if intersection == 0:
        return 0.0

    smaller_area = min(_box_area(box1), _box_area(box2))
    if smaller_area == 0:
        return 0.0
    return intersection / smaller_area


def _select_best_stamp_boxes(detections: list, overlap_threshold: float) -> list:
    """
    Unchanged logic from stamp_test.py's select_best_stamp_boxes():
    """
    selected = []
    detections = sorted(detections, key=lambda d: _box_area(d["box"]))

    for detection in detections:
        should_keep = True
        for existing in selected:
            overlap = _calculate_overlap(detection["box"], existing["box"])
            if overlap >= overlap_threshold:
                should_keep = False
                logger.debug(
                    "Ignoring larger overlapping stamp detection (confidence=%.4f, box=%s)",
                    detection["confidence"], detection["box"],
                )
                break
        if should_keep:
            selected.append(detection)

    return selected


def detect_stamps(image: Image.Image) -> list:
    """
    Runs stamp detection on a single page image (PIL.Image, RGB).

    """
    processor, model = get_stamp_model()

    inputs = processor(images=image, return_tensors="pt")
    with torch.no_grad():
        outputs = model(**inputs)

    target_sizes = torch.tensor([image.size[::-1]])
    results = processor.post_process_object_detection(
        outputs, threshold=STAMP_CONFIDENCE_THRESHOLD, target_sizes=target_sizes
    )[0]

    detections = []
    for score, box in zip(results["scores"], results["boxes"]):
        detections.append({
            "confidence": float(score),
            "box": [float(x) for x in box],
        })

    return _select_best_stamp_boxes(detections, STAMP_OVERLAP_THRESHOLD)
