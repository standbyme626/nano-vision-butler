"""Telegram entry workflow: dedup, routing, MCP invocation, and reply shaping."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from src.db.repositories.telegram_update_repo import TelegramUpdateRepo
from src.mcp_server.server import VisionButlerMCPServer
from src.security.security_guard import SecurityGuard
from src.schemas.telegram import TelegramInboundMessage, TelegramUpdate
from src.services.reply_builder import TelegramReplyBuilder
from src.settings import AppConfig


class TelegramReplyService:
    def __init__(
        self,
        *,
        update_repo: TelegramUpdateRepo,
        mcp_server: VisionButlerMCPServer,
        config: AppConfig,
        security_guard: SecurityGuard,
        reply_builder: TelegramReplyBuilder | None = None,
    ) -> None:
        self._update_repo = update_repo
        self._mcp = mcp_server
        self._config = config
        self._security_guard = security_guard
        self._reply_builder = reply_builder or TelegramReplyBuilder()

    def handle_update(self, payload: dict[str, Any], *, trace_id: str | None = None) -> dict[str, Any]:
        inbound = self._parse_inbound(payload)
        effective_trace_id = self._as_text(trace_id) or f"tg-{inbound.update_id}"
        record = TelegramUpdate(
            id=f"tgupd-{uuid4().hex[:12]}",
            update_id=inbound.update_id,
            chat_id=inbound.chat_id,
            from_user_id=inbound.from_user_id,
            message_type=inbound.message_type,
            message_text=inbound.text,
            received_at=None,
            processed_at=None,
            status="received",
            error_message=None,
            trace_id=effective_trace_id,
        )
        inserted = self._update_repo.save_telegram_update(record)
        self._commit_update_repo()
        if not inserted:
            existing = self._update_repo.get_by_update_id(inbound.update_id)
            return {
                "ok": True,
                "status": "ignored_duplicate",
                "deduplicated": True,
                "update_id": inbound.update_id,
                "previous_status": existing.status if existing else None,
                "actions": [],
                "outbound_messages": [],
            }

        try:
            self._security_guard.validate_user_access(
                inbound.from_user_id,
                trace_id=effective_trace_id,
                action="telegram_user_access",
                meta={"update_id": inbound.update_id},
            )
        except ValueError as exc:
            message = str(exc)
            self._update_repo.mark_telegram_update_failed(inbound.update_id, message)
            self._commit_update_repo()
            return {
                "ok": False,
                "status": "failed",
                "deduplicated": False,
                "update_id": inbound.update_id,
                "message_type": inbound.message_type,
                "command": inbound.command,
                "error": message,
                "actions": self._build_actions(inbound),
                "outbound_messages": self._build_error_reply(inbound.chat_id, message),
            }

        try:
            text = self._route_message(inbound=inbound, trace_id=effective_trace_id)
            outbound = self._build_reply(inbound.chat_id, text)
            self._update_repo.mark_telegram_update_processed(inbound.update_id)
            self._commit_update_repo()
            return {
                "ok": True,
                "status": "processed",
                "deduplicated": False,
                "update_id": inbound.update_id,
                "message_type": inbound.message_type,
                "command": inbound.command,
                "actions": self._build_actions(inbound),
                "outbound_messages": outbound,
            }
        except Exception as exc:
            error_message = str(exc)[:500] or "telegram_update_failed"
            self._update_repo.mark_telegram_update_failed(inbound.update_id, error_message)
            self._commit_update_repo()
            return {
                "ok": False,
                "status": "failed",
                "deduplicated": False,
                "update_id": inbound.update_id,
                "message_type": inbound.message_type,
                "command": inbound.command,
                "error": error_message,
                "actions": self._build_actions(inbound),
                "outbound_messages": self._build_error_reply(inbound.chat_id, error_message),
            }

    @staticmethod
    def command_specs() -> list[str]:
        return ["/snapshot", "/clip", "/lastseen", "/state", "/ocr", "/device", "/help"]

    def _route_message(self, *, inbound: TelegramInboundMessage, trace_id: str) -> str:
        if inbound.command:
            return self._handle_command(inbound=inbound, trace_id=trace_id)
        if inbound.message_type == "photo":
            return self._handle_photo(inbound=inbound, trace_id=trace_id)
        if inbound.message_type == "video":
            return self._handle_video(inbound=inbound, trace_id=trace_id)
        if inbound.message_type == "text":
            return self._handle_text(inbound=inbound, trace_id=trace_id)
        return TelegramReplyBuilder.build_help_text()

    def _handle_command(self, *, inbound: TelegramInboundMessage, trace_id: str) -> str:
        cmd = inbound.command or ""
        args = list(inbound.command_args)

        if cmd == "help":
            return TelegramReplyBuilder.build_help_text()

        if cmd == "snapshot":
            device_id = args[0] if args else self._default_device_id()
            result = self._call_tool(
                "take_snapshot",
                {"device_id": device_id, "trace_id": trace_id},
                user_id=inbound.from_user_id,
            )
            data = result["data"]
            return (
                "拍照完成\n"
                f"device_id: {data.get('device_id')}\n"
                f"media_id: {data.get('media_id')}\n"
                f"uri: {data.get('uri')}"
            )

        if cmd == "clip":
            device_id, duration_sec = self._parse_clip_args(args)
            result = self._call_tool(
                "get_recent_clip",
                {"device_id": device_id, "duration_sec": duration_sec, "trace_id": trace_id},
                user_id=inbound.from_user_id,
            )
            data = result["data"]
            return (
                "短视频生成完成\n"
                f"device_id: {data.get('device_id')}\n"
                f"media_id: {data.get('media_id')}\n"
                f"duration_sec: {data.get('duration_sec')}\n"
                f"uri: {data.get('uri')}"
            )

        if cmd == "lastseen":
            if not args:
                raise ValueError("object_name is required for /lastseen")
            object_name = args[0]
            camera_id = args[1] if len(args) >= 2 else None
            zone_id = args[2] if len(args) >= 3 else None
            result = self._call_tool(
                "last_seen_object",
                {
                    "object_name": object_name,
                    "camera_id": camera_id,
                    "zone_id": zone_id,
                    "trace_id": trace_id,
                },
                user_id=inbound.from_user_id,
            )
            data = result["data"]
            return (
                "最后出现结果\n"
                f"object_name: {data.get('object_name')}\n"
                f"camera_id: {data.get('camera_id')}\n"
                f"zone_id: {data.get('zone_id')}\n"
                f"observed_at: {data.get('observed_at')}"
            )

        if cmd == "state":
            if not args:
                raise ValueError("object_name is required for /state")
            object_name = args[0]
            camera_id = args[1] if len(args) >= 2 else self._default_camera_id()
            zone_id = args[2] if len(args) >= 3 else self._default_zone_id()
            result = self._call_tool(
                "get_object_state",
                {
                    "object_name": object_name,
                    "camera_id": camera_id,
                    "zone_id": zone_id,
                    "trace_id": trace_id,
                },
                user_id=inbound.from_user_id,
            )
            data = result["data"]
            return (
                "对象状态\n"
                f"object_name: {data.get('object_name')}\n"
                f"state_value: {data.get('state_value')}\n"
                f"reason_code: {data.get('reason_code')}\n"
                f"fresh_until: {data.get('fresh_until')}\n"
                f"is_stale: {bool(data.get('is_stale', 0))}"
            )

        if cmd == "ocr":
            if not args:
                raise ValueError("media_id or input_uri is required for /ocr")
            target = args[0]
            request_payload: dict[str, Any] = {"trace_id": trace_id}
            if target.startswith(("http://", "https://", "file://", "tg://")):
                request_payload["input_uri"] = target
            else:
                request_payload["media_id"] = target
            result = self._call_tool("ocr_quick_read", request_payload, user_id=inbound.from_user_id)
            data = result["data"]
            return (
                "OCR 结果\n"
                f"ocr_result_id: {data.get('ocr_result_id')}\n"
                f"confidence: {data.get('confidence')}\n"
                f"raw_text: {data.get('raw_text')}"
            )

        if cmd == "device":
            device_id = args[0] if args else self._default_device_id()
            result = self._call_tool(
                "device_status",
                {"device_id": device_id, "trace_id": trace_id},
                user_id=inbound.from_user_id,
            )
            data = result["data"]
            return (
                "设备状态\n"
                f"device_id: {data.get('device_id')}\n"
                f"status: {data.get('status')}\n"
                f"effective_status: {data.get('effective_status')}\n"
                f"last_seen: {data.get('last_seen')}"
            )

        return TelegramReplyBuilder.build_help_text()

    def _handle_photo(self, *, inbound: TelegramInboundMessage, trace_id: str) -> str:
        file_id = inbound.photo_file_id
        if not file_id:
            raise ValueError("photo_file_id missing in update")
        result = self._call_tool(
            "ocr_quick_read",
            {
                "input_uri": f"tg://photo/{file_id}.jpg",
                "trace_id": trace_id,
            },
            user_id=inbound.from_user_id,
        )
        data = result["data"]
        return (
            "图片已转入 OCR 流程\n"
            f"ocr_result_id: {data.get('ocr_result_id')}\n"
            f"confidence: {data.get('confidence')}\n"
            f"raw_text: {data.get('raw_text')}"
        )

    def _handle_video(self, *, inbound: TelegramInboundMessage, trace_id: str) -> str:
        file_id = inbound.video_file_id
        if not file_id:
            raise ValueError("video_file_id missing in update")
        result = self._call_tool(
            "ocr_quick_read",
            {
                "input_uri": f"tg://video/{file_id}.mp4",
                "trace_id": trace_id,
            },
            user_id=inbound.from_user_id,
        )
        data = result["data"]
        return (
            "视频帧已转入 OCR 流程\n"
            f"ocr_result_id: {data.get('ocr_result_id')}\n"
            f"confidence: {data.get('confidence')}\n"
            f"raw_text: {data.get('raw_text')}"
        )

    def _handle_text(self, *, inbound: TelegramInboundMessage, trace_id: str) -> str:
        question = inbound.text or ""
        world = self._call_tool(
            "get_world_state",
            {"camera_id": self._default_camera_id(), "trace_id": trace_id},
            user_id=inbound.from_user_id,
        )
        recent_events = self._call_tool(
            "query_recent_events",
            {"limit": 3, "trace_id": trace_id},
            user_id=inbound.from_user_id,
        )
        summary = world.get("summary", "")
        world_rows = int(world.get("data", {}).get("summary", {}).get("total_rows", 0))
        events = recent_events.get("data", [])
        event_lines = []
        for item in events[:3]:
            event_lines.append(
                f"- {item.get('event_at')}: {item.get('event_type')} / {item.get('summary')}"
            )
        timeline = "\n".join(event_lines) if event_lines else "- 无最近事件"
        return (
            f"收到问题：{question}\n"
            f"世界状态摘要：{summary}\n"
            f"当前条目数：{world_rows}\n"
            f"最近事件：\n{timeline}"
        )

    def _call_tool(
        self,
        tool_name: str,
        args: dict[str, Any],
        *,
        user_id: str | None,
        skill_name: str = "telegram",
    ) -> dict[str, Any]:
        payload = dict(args)
        payload.setdefault("user_id", user_id)
        payload.setdefault("skill_name", skill_name)
        response = self._mcp.call_tool(tool_name, payload)
        if not response.get("ok"):
            raise ValueError(response.get("summary", f"Tool call failed: {tool_name}"))
        return response

    def _build_actions(self, inbound: TelegramInboundMessage) -> list[dict[str, str]]:
        if not inbound.chat_id:
            return []
        action = "typing"
        if inbound.message_type == "photo" or inbound.command == "snapshot":
            action = "upload_photo"
        elif inbound.message_type == "video":
            action = "upload_video"
        elif inbound.command == "clip":
            action = "record_video"
        return [{"method": "sendChatAction", "chat_id": inbound.chat_id, "action": action}]

    def _build_reply(self, chat_id: str | None, text: str) -> list[dict[str, str]]:
        if not chat_id:
            return []
        return self._reply_builder.build_outbound_messages(chat_id=chat_id, text=text)

    def _build_error_reply(self, chat_id: str | None, error_message: str) -> list[dict[str, str]]:
        if not chat_id:
            return []
        text = f"请求处理失败：{error_message}"
        return self._reply_builder.build_outbound_messages(chat_id=chat_id, text=text)

    def _default_device_id(self) -> str:
        devices = self._config.devices.get("devices", []) if isinstance(self._config.devices, dict) else []
        if devices and isinstance(devices[0], dict):
            value = self._as_text(devices[0].get("device_id"))
            if value:
                return value
        return "rk3566-dev-01"

    def _default_camera_id(self) -> str | None:
        cameras = self._config.cameras.get("cameras", []) if isinstance(self._config.cameras, dict) else []
        if cameras and isinstance(cameras[0], dict):
            return self._as_text(cameras[0].get("camera_id"))
        return None

    def _default_zone_id(self) -> str | None:
        cameras = self._config.cameras.get("cameras", []) if isinstance(self._config.cameras, dict) else []
        if cameras and isinstance(cameras[0], dict):
            zones = cameras[0].get("zones")
            if isinstance(zones, list) and zones and isinstance(zones[0], dict):
                return self._as_text(zones[0].get("zone_id"))
        return None

    def _parse_clip_args(self, args: list[str]) -> tuple[str, int]:
        device_id = self._default_device_id()
        duration_sec = 10
        if not args:
            return device_id, duration_sec
        if len(args) == 1:
            maybe_duration = self._to_int(args[0])
            if maybe_duration is not None:
                return device_id, maybe_duration
            return args[0], duration_sec

        device_id = args[0]
        parsed = self._to_int(args[1])
        if parsed is None:
            raise ValueError("duration_sec must be integer for /clip")
        return device_id, parsed

    def _parse_inbound(self, payload: dict[str, Any]) -> TelegramInboundMessage:
        if not isinstance(payload, dict):
            raise ValueError("telegram update payload must be an object")
        update_id = self._as_text(payload.get("update_id"))
        if not update_id:
            raise ValueError("update_id is required")

        message = payload.get("message") or payload.get("edited_message")
        if not isinstance(message, dict):
            raise ValueError("message is required in telegram update payload")

        chat = message.get("chat") if isinstance(message.get("chat"), dict) else {}
        from_user = message.get("from") if isinstance(message.get("from"), dict) else {}

        chat_id = self._as_text(chat.get("id"))
        from_user_id = self._as_text(from_user.get("id"))
        text = self._as_text(message.get("text")) or self._as_text(message.get("caption"))
        command, command_args = self._parse_command(text)

        photo_file_id = self._extract_photo_file_id(message.get("photo"))
        video_file_id = self._extract_video_file_id(message.get("video"))

        if command:
            message_type = "command"
        elif photo_file_id:
            message_type = "photo"
        elif video_file_id:
            message_type = "video"
        elif text:
            message_type = "text"
        else:
            message_type = "unsupported"

        return TelegramInboundMessage(
            update_id=update_id,
            chat_id=chat_id,
            from_user_id=from_user_id,
            message_type=message_type,
            text=text,
            command=command,
            command_args=command_args,
            photo_file_id=photo_file_id,
            video_file_id=video_file_id,
        )

    @staticmethod
    def _parse_command(text: str | None) -> tuple[str | None, tuple[str, ...]]:
        if not text:
            return None, ()
        tokens = text.strip().split()
        if not tokens:
            return None, ()
        first = tokens[0]
        if not first.startswith("/"):
            return None, ()
        command = first[1:].split("@")[0].lower()
        return command, tuple(tokens[1:])

    @staticmethod
    def _extract_photo_file_id(raw_photo: Any) -> str | None:
        if not isinstance(raw_photo, list) or not raw_photo:
            return None
        candidate = raw_photo[-1]
        if not isinstance(candidate, dict):
            return None
        file_id = candidate.get("file_id")
        return str(file_id).strip() if file_id is not None and str(file_id).strip() else None

    @staticmethod
    def _extract_video_file_id(raw_video: Any) -> str | None:
        if not isinstance(raw_video, dict):
            return None
        file_id = raw_video.get("file_id")
        return str(file_id).strip() if file_id is not None and str(file_id).strip() else None

    @staticmethod
    def _to_int(value: Any) -> int | None:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return None
        return max(parsed, 1)

    @staticmethod
    def _as_text(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text if text else None

    def _commit_update_repo(self) -> None:
        self._update_repo.conn.commit()
