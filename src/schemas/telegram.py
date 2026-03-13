"""Schema models for telegram update dedup/processing entities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class TelegramUpdate:
    id: str
    update_id: str
    chat_id: str | None
    from_user_id: str | None
    message_type: str | None
    message_text: str | None
    received_at: str | None
    processed_at: str | None
    status: str
    error_message: str | None
    trace_id: str | None

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "TelegramUpdate":
        return cls(**dict(row))


@dataclass(frozen=True)
class TelegramInboundMessage:
    update_id: str
    chat_id: str | None
    from_user_id: str | None
    message_type: str
    text: str | None
    command: str | None
    command_args: tuple[str, ...]
    photo_file_id: str | None
    video_file_id: str | None


@dataclass(frozen=True)
class TelegramOutboundMessage:
    method: str
    chat_id: str
    text: str
