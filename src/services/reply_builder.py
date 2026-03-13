"""Telegram-focused reply formatting helpers."""

from __future__ import annotations

from src.schemas.telegram import TelegramOutboundMessage


class TelegramReplyBuilder:
    """Builds Telegram-safe text replies with automatic chunk splitting."""

    def __init__(self, *, max_message_chars: int = 3500) -> None:
        self.max_message_chars = max_message_chars

    def split_long_text(self, text: str) -> list[str]:
        normalized = (text or "").strip()
        if not normalized:
            return [""]
        if len(normalized) <= self.max_message_chars:
            return [normalized]

        chunks: list[str] = []
        remaining = normalized
        threshold = int(self.max_message_chars * 0.6)

        while len(remaining) > self.max_message_chars:
            split_at = remaining.rfind("\n", 0, self.max_message_chars + 1)
            if split_at < threshold:
                split_at = remaining.rfind(" ", 0, self.max_message_chars + 1)
            if split_at < threshold:
                split_at = self.max_message_chars

            chunk = remaining[:split_at].strip()
            if not chunk:
                chunk = remaining[: self.max_message_chars]
                split_at = len(chunk)
            chunks.append(chunk)
            remaining = remaining[split_at:].strip()

        if remaining:
            chunks.append(remaining)
        return chunks

    def build_outbound_messages(self, *, chat_id: str, text: str) -> list[dict[str, str]]:
        messages = []
        for chunk in self.split_long_text(text):
            outbound = TelegramOutboundMessage(method="sendMessage", chat_id=chat_id, text=chunk)
            messages.append(
                {
                    "method": outbound.method,
                    "chat_id": outbound.chat_id,
                    "text": outbound.text,
                }
            )
        return messages

    @staticmethod
    def build_help_text() -> str:
        return (
            "Vision Butler 命令：\n"
            "/snapshot [device_id]\n"
            "/clip [device_id] [duration_sec]\n"
            "/lastseen <object_name> [camera_id] [zone_id]\n"
            "/state <object_name> [camera_id] [zone_id]\n"
            "/ocr <media_id|input_uri>\n"
            "/device [device_id]\n"
            "/help"
        )
