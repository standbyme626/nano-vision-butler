"""FastAPI routes for Telegram update ingestion and reply shaping."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends

from src.dependencies import TelegramReplyService, api_success, get_telegram_reply_service

router = APIRouter(prefix="/telegram", tags=["telegram"])


@router.post("/update")
def handle_update(
    payload: dict[str, Any] = Body(...),
    service: TelegramReplyService = Depends(get_telegram_reply_service),
) -> dict:
    return api_success(service.handle_update(payload))


@router.get("/commands")
def list_commands(
    service: TelegramReplyService = Depends(get_telegram_reply_service),
) -> dict:
    return api_success({"commands": service.command_specs()})
