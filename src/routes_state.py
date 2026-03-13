"""FastAPI routes for state query APIs."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from src.dependencies import StateQueryService, api_success, get_state_service

router = APIRouter(prefix="/memory", tags=["state"])


@router.get("/object-state")
def object_state(
    object_name: str = Query(...),
    camera_id: str | None = Query(default=None),
    zone_id: str | None = Query(default=None),
    service: StateQueryService = Depends(get_state_service),
) -> dict:
    return api_success(service.object_state(object_name=object_name, camera_id=camera_id, zone_id=zone_id))


@router.get("/zone-state")
def zone_state(
    camera_id: str = Query(...),
    zone_id: str = Query(...),
    service: StateQueryService = Depends(get_state_service),
) -> dict:
    return api_success(service.zone_state(camera_id=camera_id, zone_id=zone_id))


@router.get("/world-state")
def world_state(
    camera_id: str | None = Query(default=None),
    service: StateQueryService = Depends(get_state_service),
) -> dict:
    result = service.world_state(camera_id=camera_id)
    return api_success(result)
