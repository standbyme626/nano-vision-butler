"""FastAPI routes for memory query APIs."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from src.dependencies import MemoryQueryService, api_success, get_memory_service

router = APIRouter(prefix="/memory", tags=["memory"])


@router.get("/recent-events")
def recent_events(
    zone_id: str | None = Query(default=None),
    object_name: str | None = Query(default=None),
    start_time: str | None = Query(default=None),
    end_time: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=200),
    service: MemoryQueryService = Depends(get_memory_service),
) -> dict:
    events = service.recent_events(
        zone_id=zone_id,
        object_name=object_name,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
    )
    return api_success(events)


@router.get("/last-seen")
def last_seen(
    object_name: str = Query(...),
    camera_id: str | None = Query(default=None),
    zone_id: str | None = Query(default=None),
    service: MemoryQueryService = Depends(get_memory_service),
) -> dict:
    result = service.last_seen(object_name=object_name, camera_id=camera_id, zone_id=zone_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"No observation found for {object_name}")
    return api_success(result)
