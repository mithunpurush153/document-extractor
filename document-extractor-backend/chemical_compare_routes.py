"""Runtime two-PDF chemical validation endpoint."""

from __future__ import annotations

import os
import tempfile

from fastapi import APIRouter, File, HTTPException, UploadFile

from config import ALLOWED_EXTENSIONS, MAX_UPLOAD_SIZE_MB
from services.dynamic_chemical_validator import validate_two_documents
from services.ocr_service import ocr_pages
from services.pdf_service import pdf_to_images
from services.table_extractor import extract_all_tables

router = APIRouter(prefix="/chemical", tags=["chemical-validation"])


def _extract_document(pdf_bytes: bytes) -> dict:
    if not pdf_bytes:
        raise ValueError("Uploaded PDF is empty")
    if len(pdf_bytes) > MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise ValueError(f"PDF exceeds the {MAX_UPLOAD_SIZE_MB} MB upload limit")

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(pdf_bytes)
        path = tmp.name
    try:
        page_images = pdf_to_images(path)
        raw_output = ocr_pages(page_images)
        tables = extract_all_tables(raw_output)
        text = " ".join(
            str(d.get("text", ""))
            for page in raw_output.values()
            for d in page
            if isinstance(d, dict) and d.get("text")
        )
        return {"tables": tables, "text": text, "ocr": raw_output}
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


@router.post("/validate")
async def validate_documents(
    reference_pdf: UploadFile = File(...),
    test_pdf: UploadFile = File(...),
):
    for upload, label in ((reference_pdf, "Reference PDF"), (test_pdf, "Test Report PDF")):
        ext = os.path.splitext(upload.filename or "")[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail=f"{label} must be a PDF")

    try:
        reference_bytes = await reference_pdf.read()
        test_bytes = await test_pdf.read()
        reference_extraction = _extract_document(reference_bytes)
        test_extraction = _extract_document(test_bytes)
        result = validate_two_documents(
            reference_extraction["tables"],
            test_extraction["tables"],
            reference_extraction["text"],
            test_extraction["text"],
            reference_ocr=reference_extraction["ocr"],
            test_ocr=test_extraction["ocr"],
        )
        result["reference_filename"] = reference_pdf.filename
        result["test_filename"] = test_pdf.filename
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Chemical validation failed: {exc}") from exc