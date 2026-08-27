"""
API routes.

Handles:
- PDF upload
- PDF-to-image conversion
- OCR
- table extraction
- stamp detection
- signature detection
- stamp/signature crop saving
- JSON result download
"""

import json
import logging
import os
import shutil
import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from PIL import Image

from config import (
    ALLOWED_EXTENSIONS,
    CROP_DIR,
    MAX_UPLOAD_SIZE_MB,
    OUTPUT_DIR,
    UPLOAD_DIR,
)
from schemas import ExtractionResponse
from services.chemical_validator import ChemicalValidator
from services.ocr_service import ocr_pages
from services.pdf_service import pdf_to_images
from services.signature_detector import detect_signatures
from services.stamp_detector import detect_stamps
from services.table_extractor import extract_all_tables


logger = logging.getLogger(__name__)

router = APIRouter()

# Document-level chemical validator. It is additive to the existing extraction pipeline.
chemical_validator = ChemicalValidator()


def _save_crop(
    image: Image.Image,
    box: list,
    output_path: str,
) -> None:
    """
    Crop a detected region from a page image and save it as PNG.

    The bounding box is:
    [x1, y1, x2, y2]
    """

    width, height = image.size

    x1 = max(0, min(int(box[0]), width))
    y1 = max(0, min(int(box[1]), height))
    x2 = max(0, min(int(box[2]), width))
    y2 = max(0, min(int(box[3]), height))

    # Ignore invalid/empty boxes.
    if x2 <= x1 or y2 <= y1:
        raise ValueError(f"Invalid crop box: {box}")

    crop = image.crop((x1, y1, x2, y2))
    crop.save(output_path, format="PNG")


@router.post("/extract", response_model=ExtractionResponse)
async def extract_tables(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename)[1].lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Only PDF is accepted.",
        )

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(CROP_DIR, exist_ok=True)

    job_id = uuid.uuid4().hex
    saved_path = os.path.join(UPLOAD_DIR, f"{job_id}{ext}")
    job_crop_dir = os.path.join(CROP_DIR, job_id)

    try:
        # ---------------------------------------------------------
        # 1. Save uploaded PDF
        # ---------------------------------------------------------

        with open(saved_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        size_mb = os.path.getsize(saved_path) / (1024 * 1024)

        if size_mb > MAX_UPLOAD_SIZE_MB:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"File too large ({size_mb:.1f} MB). "
                    f"Max is {MAX_UPLOAD_SIZE_MB} MB."
                ),
            )

        logger.info(
            "Processing '%s' (%.1f KB, job_id=%s)",
            file.filename,
            size_mb * 1024,
            job_id,
        )

        # ---------------------------------------------------------
        # 2. Convert PDF to page images
        #
        # This is the EXISTING pipeline.
        # We reuse these exact images for OCR, stamps and signatures.
        # ---------------------------------------------------------

        page_images = pdf_to_images(saved_path)

        # ---------------------------------------------------------
        # 3. Existing OCR pipeline — UNCHANGED
        # ---------------------------------------------------------

        raw_output = ocr_pages(page_images)

        # ---------------------------------------------------------
        # 4. Existing table extraction — UNCHANGED
        # ---------------------------------------------------------

        tables_by_page = extract_all_tables(raw_output)

        # ---------------------------------------------------------
        # 5. New stamp/signature detection pipeline
        # ---------------------------------------------------------

        detections_by_page = {}

        os.makedirs(job_crop_dir, exist_ok=True)

        for page_index, page_array in enumerate(page_images):
            page_number = page_index + 1
            page_key = f"page_{page_number}"

            logger.info(
                "Running stamp/signature detection on %s",
                page_key,
            )

            # pdf_service.py returns RGB NumPy arrays.
            # Convert the existing image to PIL in memory.
            page_image = Image.fromarray(page_array).convert("RGB")

            # -----------------------------------------------------
            # Stamp detection
            # -----------------------------------------------------

            stamp_detections = detect_stamps(page_image)

            stamp_results = []

            for stamp_index, detection in enumerate(
                stamp_detections,
                start=1,
            ):
                crop_filename = (
                    f"page_{page_number}_stamp_{stamp_index}.png"
                )

                crop_path = os.path.join(
                    job_crop_dir,
                    crop_filename,
                )

                _save_crop(
                    page_image,
                    detection["box"],
                    crop_path,
                )

                stamp_results.append(
                    {
                        "confidence": round(
                            float(detection["confidence"]),
                            4,
                        ),
                        "image_url": (
                            f"/crops/{job_id}/{crop_filename}"
                        ),
                    }
                )

            # -----------------------------------------------------
            # Signature detection
            # -----------------------------------------------------

            signature_detections = detect_signatures(page_image)

            signature_results = []

            for signature_index, detection in enumerate(
                signature_detections,
                start=1,
            ):
                crop_filename = (
                    f"page_{page_number}_signature_{signature_index}.png"
                )

                crop_path = os.path.join(
                    job_crop_dir,
                    crop_filename,
                )

                _save_crop(
                    page_image,
                    detection["box"],
                    crop_path,
                )

                signature_results.append(
                    {
                        "confidence": round(
                            float(detection["confidence"]),
                            4,
                        ),
                        "image_url": (
                            f"/crops/{job_id}/{crop_filename}"
                        ),
                    }
                )

            detections_by_page[page_key] = {
                "stamps": stamp_results,
                "signatures": signature_results,
            }

            logger.info(
                "%s: stamps=%d, signatures=%d",
                page_key,
                len(stamp_results),
                len(signature_results),
            )

        # ---------------------------------------------------------
        # 6. Chemical validation (NEW, document-level)
        #
        # Consumes the EXISTING tables_by_page structure. The table extractor
        # itself is not changed, and failures here never break extraction.
        # ---------------------------------------------------------

        extraction_context = {"tables_by_page": tables_by_page}
        try:
            chemical_validation = chemical_validator.validate_supplier_document(
                extraction_context
            )
        except Exception as chemical_error:
            logger.exception("Chemical validation failed for job_id=%s", job_id)
            chemical_validation = {
                "identified_standard": None,
                "identified_grade": None,
                "validation_result": None,
                "error": str(chemical_error),
            }

        # ---------------------------------------------------------
        # 7. Existing JSON output
        #
        # IMPORTANT: Keep this exactly as the old project did.
        # The downloaded JSON remains tables_by_page.
        # ---------------------------------------------------------

        output_path = os.path.join(
            OUTPUT_DIR,
            f"{job_id}.json",
        )

        with open(
            output_path,
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(
                tables_by_page,
                f,
                indent=2,
                ensure_ascii=False,
            )

        # ---------------------------------------------------------
        # 7. API response
        # ---------------------------------------------------------

        return ExtractionResponse(
            job_id=job_id,
            filename=file.filename,
            total_pages=len(page_images),
            tables_by_page=tables_by_page,
            detections_by_page=detections_by_page,
            chemical_validation=chemical_validation,
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.exception(
            "Extraction failed for '%s'",
            file.filename,
        )

        raise HTTPException(
            status_code=500,
            detail=f"Processing failed: {str(e)}",
        )

    finally:
        # Uploaded PDF does not need to remain after processing.
        if os.path.exists(saved_path):
            os.remove(saved_path)


@router.get("/download/{job_id}")
async def download_result(job_id: str):
    """
    Download the existing extracted-table JSON.
    """

    output_path = os.path.join(
        OUTPUT_DIR,
        f"{job_id}.json",
    )

    if not os.path.exists(output_path):
        raise HTTPException(
            status_code=404,
            detail="Result not found or expired.",
        )

    return FileResponse(
        output_path,
        media_type="application/json",
        filename=f"extracted_tables_{job_id}.json",
    )


@router.get("/crops/{job_id}/{filename}")
async def get_crop(job_id: str, filename: str):
    """
    Serve a generated stamp/signature crop.

    Only files directly inside crops/{job_id}/ are allowed.
    """

    # Prevent path traversal such as ../../some_file
    if os.path.basename(filename) != filename:
        raise HTTPException(
            status_code=400,
            detail="Invalid filename.",
        )

    crop_path = os.path.join(
        CROP_DIR,
        job_id,
        filename,
    )

    if not os.path.isfile(crop_path):
        raise HTTPException(
            status_code=404,
            detail="Crop not found.",
        )

    return FileResponse(
        crop_path,
        media_type="image/png",
    )