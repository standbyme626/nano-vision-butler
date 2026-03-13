"""FastAPI routes for policy APIs."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from src.dependencies import PolicyService, api_success, get_policy_service

router = APIRouter(prefix="/policy", tags=["policy"])


@router.get("/evaluate-staleness")
def evaluate_staleness(
    object_name: str = Query(...),
    camera_id: str | None = Query(default=None),
    zone_id: str | None = Query(default=None),
    query_text: str | None = Query(default=None),
    query_type: str | None = Query(default=None),
    service: PolicyService = Depends(get_policy_service),
) -> dict:
    result = service.evaluate_staleness(
        object_name=object_name,
        camera_id=camera_id,
        zone_id=zone_id,
        query_text=query_text,
        query_type=query_type,
    )
    return api_success(result)
