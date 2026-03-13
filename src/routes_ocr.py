"""FastAPI routes for OCR APIs."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends

from src.dependencies import OCRService, api_success, get_ocr_service

router = APIRouter(prefix="/ocr", tags=["ocr"])


@router.post("/quick-read")
def quick_read(
    payload: dict[str, Any] = Body(...),
    service: OCRService = Depends(get_ocr_service),
) -> dict:
    return api_success(service.quick_read(payload))


@router.post("/extract-fields")
def extract_fields(
    payload: dict[str, Any] = Body(...),
    service: OCRService = Depends(get_ocr_service),
) -> dict:
    return api_success(service.extract_fields(payload))
