"""FastAPI routes for device APIs."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query

from src.dependencies import DeviceService, api_success, get_device_service

router = APIRouter(prefix="/device", tags=["device"])


@router.get("/status")
def device_status(
    device_id: str = Query(...),
    service: DeviceService = Depends(get_device_service),
) -> dict:
    result = service.get_status(device_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Device not found: {device_id}")
    return api_success(result)


@router.post("/command/take-snapshot")
def take_snapshot(
    payload: dict[str, Any] = Body(...),
    service: DeviceService = Depends(get_device_service),
) -> dict:
    return api_success(service.command_take_snapshot(payload))


@router.post("/command/get-recent-clip")
def get_recent_clip(
    payload: dict[str, Any] = Body(...),
    service: DeviceService = Depends(get_device_service),
) -> dict:
    return api_success(service.command_get_recent_clip(payload))


@router.post("/ingest/event")
def ingest_event(
    payload: dict[str, Any] = Body(...),
    service: DeviceService = Depends(get_device_service),
) -> dict:
    return api_success(service.ingest_event(payload))


@router.post("/heartbeat")
def heartbeat(
    payload: dict[str, Any] = Body(...),
    service: DeviceService = Depends(get_device_service),
) -> dict:
    return api_success(service.heartbeat(payload))
