"""
Central configuration for the OCR + table extraction pipeline.

"""

# --- PDF rendering (Cell 4: Convert PDF pages to images) ---
DPI = 300
ZOOM = DPI / 72

# --- OCR rotation retry (Cell 7: Run OCR with automatic rotation retry) ---
CONFIDENCE_RETRY_THRESHOLD = 0.45
MIN_DETECTIONS_RETRY = 3
ROTATION_ANGLES_TO_TRY = [90, 180, 270]

# --- Row grouping (Cell 12: Group OCR detections into rows) ---
ROW_Y_TOLERANCE_RATIO = 0.6

# --- Table block detection (Cell 13: Detect contiguous table blocks) ---
MIN_COLS_FOR_TABLE = 2
GAP_FACTOR = 5
MIN_ROWS_PER_BLOCK = 2
COL_COUNT_TOLERANCE = 3

# --- Column detection (Cell 14: Detect column boundaries) ---
COLUMN_TOLERANCE_MULTIPLIER = 1.5

# --- Header detection (Cell 15: Convert table block into DataFrame) ---
HEADER_NUMERIC_RATIO_THRESHOLD = 0.4

# --- EasyOCR ---
OCR_LANGUAGES = ["en"]

# --- File handling (new — not in the notebook) ---
UPLOAD_DIR = "uploads"
OUTPUT_DIR = "outputs"
ALLOWED_EXTENSIONS = {".pdf"}
MAX_UPLOAD_SIZE_MB = 25

# --- Stamp detection ---

STAMP_MODEL_DIR = "models/stamp_model"
STAMP_CONFIDENCE_THRESHOLD = 0.5
STAMP_OVERLAP_THRESHOLD = 0.5

# --- Signature detection ---

SIGNATURE_MODEL_DIR = "models/signature_model"
SIGNATURE_MODEL_PATH = "models/signature_model/best.pt"
SIGNATURE_CONFIDENCE_THRESHOLD = 0.25

# --- Stamp / signature crop output ---

CROP_DIR = "crops"