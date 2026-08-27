"""
FastAPI application entrypoint.

Run with:
uvicorn main:app --reload
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import router
from chemical_compare_routes import router as chemical_compare_router
from services.ocr_service import get_reader
from services.stamp_detector import get_stamp_model
from services.signature_detector import get_signature_model


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


app = FastAPI(
    title="Document Table Extractor",
    version="1.0.0"
)


# Allow the React dev server to call this API.
# Tighten this list before deploying anywhere beyond localhost.

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(router)
app.include_router(chemical_compare_router)

@app.on_event("startup")
def load_models():
    # Existing OCR model
    logger.info("Loading EasyOCR model...")
    get_reader()
    logger.info("EasyOCR model ready.")

    # New stamp detection model
    logger.info("Loading stamp detection model...")
    get_stamp_model()
    logger.info("Stamp detection model ready.")

    # New signature detection model
    logger.info("Loading signature detection model...")
    get_signature_model()
    logger.info("Signature detection model ready.")


@app.get("/health")
def health_check():
    return {"status": "ok"}