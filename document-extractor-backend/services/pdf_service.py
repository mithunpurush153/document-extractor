import logging
 
import cv2
import fitz  # PyMuPDF
import numpy as np
 
from config import ZOOM
 
logger = logging.getLogger(__name__)
 
# 1-indexed page number -> clockwise degrees needed to make it upright.
# Verified against the real ABB_Report.pdf by rendering pages 3 and 7
# and testing rotation directions directly against the actual content.
MANUAL_ROTATION_OVERRIDES = {}
 
 
def _apply_manual_rotation(img, angle: int):
    if angle == 90:
        return cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
    elif angle == 180:
        return cv2.rotate(img, cv2.ROTATE_180)
    elif angle == 270:
        return cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
    return img
 
 
def pdf_to_images(pdf_path: str) -> list:
    """
    Convert PDF pages to RGB images, applying MANUAL_ROTATION_OVERRIDES
    for any page listed above. Nothing else touches rotation in this
    function — see module docstring for why a second, generic
    "if landscape, rotate" check was removed.
    """
    doc = fitz.open(pdf_path)
    page_images = []
 
    matrix = fitz.Matrix(ZOOM, ZOOM)
    for i, page in enumerate(doc):
        page_number = i + 1
        pix = page.get_pixmap(matrix=matrix)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        if pix.n == 4:
            img = cv2.cvtColor(img, cv2.COLOR_RGBA2RGB)
 
        if page_number in MANUAL_ROTATION_OVERRIDES:
            angle = MANUAL_ROTATION_OVERRIDES[page_number]
            logger.info("Page %d: applying manual rotation override (%d° CW)", page_number, angle)
            img = _apply_manual_rotation(img, angle)
 
        page_images.append(img)
 
    doc.close()
    logger.info("Converted %d page(s) from PDF at %d DPI", len(page_images), int(ZOOM * 72))
    return page_images
 