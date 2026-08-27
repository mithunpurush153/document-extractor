"""
Shared low-level helpers used across the OCR/table-extraction pipeline.

"""


def get_box_metrics(bbox: list) -> dict:
    """
    Given an EasyOCR bounding box (4 corner points as [[x, y], ...]),
    compute min/max x/y, vertical center, and height.
    """
    xs = [p[0] for p in bbox]
    ys = [p[1] for p in bbox]
    return {
        "x_min": min(xs), "x_max": max(xs),
        "y_min": min(ys), "y_max": max(ys),
        "y_center": (min(ys) + max(ys)) / 2,
        "height": max(ys) - min(ys),
    }


def is_numeric(text: str) -> bool:
    """Returns True if text can be parsed as a float once commas are stripped."""
    cleaned = text.replace(",", "").strip()
    try:
        float(cleaned)
        return True
    except ValueError:
        return False
