"""
Pydantic response models for the API.
"""

from typing import Any

from pydantic import BaseModel


class TableResult(BaseModel):
    rows: int
    cols: int
    columns: list[str]
    data: list[dict]


class DetectionResult(BaseModel):
    confidence: float
    image_url: str


class PageDetections(BaseModel):
    stamps: list[DetectionResult]
    signatures: list[DetectionResult]


class ExtractionResponse(BaseModel):
    job_id: str
    filename: str
    total_pages: int
    tables_by_page: dict[str, list[TableResult]]
    detections_by_page: dict[str, PageDetections]

    # NEW: document-level chemical validation.
    # Existing response fields above remain unchanged.
    chemical_validation: dict[str, Any] | None = None