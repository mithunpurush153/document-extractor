import truststore
truststore.inject_into_ssl()
import logging

import cv2
import torch
from doctr.models import ocr_predictor

from config import CONFIDENCE_RETRY_THRESHOLD, MIN_DETECTIONS_RETRY, ROTATION_ANGLES_TO_TRY

logger = logging.getLogger(__name__)

_reader = None  # lazily-initialized singleton, populated by get_reader()


def get_reader():
   
    global _reader
    if _reader is None:
        use_gpu = torch.cuda.is_available()
        logger.info("Initializing DocTR predictor (GPU=%s)", use_gpu)
        _reader = ocr_predictor(pretrained=True)
        if use_gpu:
            _reader = _reader.cuda()
    return _reader


def rotate_image(img, angle: int):
    """Unchanged."""
    if angle == 0:
        return img
    elif angle == 90:
        return cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
    elif angle == 180:
        return cv2.rotate(img, cv2.ROTATE_180)
    elif angle == 270:
        return cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
    return img


def _word_to_bbox(geometry, page_height: float, page_width: float) -> list:
    """
    Converts a DocTR word's relative geometry into the EasyOCR-shaped
    
    """
    if len(geometry) == 2:
        (x_min, y_min), (x_max, y_max) = geometry
        x_min, x_max = x_min * page_width, x_max * page_width
        y_min, y_max = y_min * page_height, y_max * page_height
        return [[x_min, y_min], [x_max, y_min], [x_max, y_max], [x_min, y_max]]

    # Rotated/4-point geometry (only occurs if assume_straight_pages=False
    # is ever set on the predictor) — scale each point the same way.
    return [[px * page_width, py * page_height] for px, py in geometry]


def _run_ocr(img):
    """
    Runs DocTR on a single page image and flattens the result .
    
    """
    reader = get_reader()
    result = reader([img])
    page = result.pages[0]
    page_height, page_width = page.dimensions

    results = []
    for block in page.blocks:
        for line in block.lines:
            for word in line.words:
                bbox = _word_to_bbox(word.geometry, page_height, page_width)
                results.append((bbox, word.value, float(word.confidence)))

    if len(results) == 0:
        return results, 0.0
    avg_conf = sum(r[2] for r in results) / len(results)
    return results, avg_conf


def _pick_best(candidates: dict) -> int:
    """Picks the rotation with the most detected words; avg confidence only breaks a tie."""
    return max(candidates, key=lambda angle: (len(candidates[angle][0]), candidates[angle][1]))


def run_ocr_with_rotation_retry(img) -> dict:
   
    height, width = img.shape[:2]

    results_0, conf_0 = _run_ocr(img)

    if len(results_0) >= MIN_DETECTIONS_RETRY and conf_0 >= CONFIDENCE_RETRY_THRESHOLD:
        results, avg_conf, rotation_used = results_0, conf_0, 0
    else:
        candidates = {0: (results_0, conf_0)}
        for angle in ROTATION_ANGLES_TO_TRY:
            candidates[angle] = _run_ocr(rotate_image(img, angle))
        rotation_used = _pick_best(candidates)
        results, avg_conf = candidates[rotation_used]

    print(
        f"PAGE DEBUG -> rotation={rotation_used}, "
        f"words={len(results)}, confidence={avg_conf:.3f}"
    )
    if len(results) < MIN_DETECTIONS_RETRY:
        logger.warning(
            "Only %d words detected after correcting to %d° — worth checking this page manually.",
            len(results), rotation_used,
        )

    return {
        "rotation_used": rotation_used,
        "avg_confidence": round(float(avg_conf), 4),
        "results": results,
    }


def ocr_pages(page_images: list) -> dict:
    """
    Unchanged. Runs OCR across every page image and returns a dict
   """
    raw_output = {}
    for i, img in enumerate(page_images):
        page_result = run_ocr_with_rotation_retry(img)
        page_key = f"page_{i + 1}"

        detections = []
        for bbox, text, conf in page_result["results"]:
            detections.append({
                "text": text,
                "confidence": float(conf),
                "bbox": [[float(x), float(y)] for x, y in bbox],
            })
        raw_output[page_key] = detections

        logger.info(
            "%s: rotation=%d, detections=%d, avg_conf=%.3f",
            page_key, page_result["rotation_used"], len(detections), page_result["avg_confidence"],
        )

    return raw_output