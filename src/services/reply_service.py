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
    _SCENE_KEYWORDS = (
        "现在",
        "当前",
        "门口",
        "环境",
        "场景",
        "画面",
        "看到",
        "情况",
        "分析",
        "现场",
        "scene",
    )
    _HISTORY_KEYWORDS = ("最近", "发生", "历史", "timeline", "recent", "event")
    _LAST_SEEN_KEYWORDS = ("最后一次", "最后出现", "上次", "last seen")
    _OBJECT_STATE_KEYWORDS = ("还在", "在不在", "still", "状态", "present")
    _ZONE_STATE_KEYWORDS = ("区域", "zone", "门口", "走廊", "客厅", "有人", "有物")

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
        question = (inbound.text or "").strip()
        intent = self._detect_text_intent(question)
        if intent == "scene":
            return self._handle_scene_text_query(inbound=inbound, trace_id=trace_id, question=question)
        if intent == "history":
            return self._handle_recent_events_text_query(inbound=inbound, trace_id=trace_id, question=question)
        if intent == "last_seen":
            return self._handle_last_seen_text_query(inbound=inbound, trace_id=trace_id, question=question)
        if intent == "object_state":
            return self._handle_object_state_text_query(inbound=inbound, trace_id=trace_id, question=question)
        if intent == "zone_state":
            return self._handle_zone_state_text_query(inbound=inbound, trace_id=trace_id, question=question)
        return self._build_world_event_summary(
            question=question,
            trace_id=trace_id,
            user_id=inbound.from_user_id,
        )

    def _handle_scene_text_query(self, *, inbound: TelegramInboundMessage, trace_id: str, question: str) -> str:
        user_id = inbound.from_user_id
        device_id = self._default_device_id()
        camera_id = self._default_camera_id() or "cam-entry-01"
        zone_id = self._default_zone_id()

        snapshot_uri: str | None = None
        snapshot_media_id: str | None = None
        snapshot_warning: str | None = None
        try:
            snapshot = self._call_tool(
                "take_snapshot",
                {
                    "device_id": device_id,
                    "camera_id": camera_id,
                    "trace_id": trace_id,
                },
                user_id=user_id,
            )
            snapshot_data = snapshot.get("data", {})
            snapshot_uri = self._as_text(snapshot_data.get("uri"))
            snapshot_media_id = self._as_text(snapshot_data.get("media_id"))
            camera_id = self._as_text(snapshot_data.get("camera_id")) or camera_id
        except ValueError as exc:
            snapshot_warning = f"实时抓拍失败，已回退历史证据：{exc}"

        if not zone_id:
            zone_id = self._resolve_zone_id(camera_id=camera_id, trace_id=trace_id, user_id=user_id)
        zone_id = zone_id or "entry_door"

        try:
            scene = self._call_tool(
                "describe_scene",
                {
                    "camera_id": camera_id,
                    "zone_id": zone_id,
                    "limit": 5,
                    "trace_id": trace_id,
                },
                user_id=user_id,
            )
        except ValueError:
            fallback = self._build_world_event_summary(question=question, trace_id=trace_id, user_id=user_id)
            if snapshot_warning:
                return f"{snapshot_warning}\n{fallback}"
            return fallback

        scene_data = scene.get("data", {})
        zone_state = scene_data.get("zone_state", {}) if isinstance(scene_data, dict) else {}
        observations = scene_data.get("observations", []) if isinstance(scene_data, dict) else []
        events = scene_data.get("events", []) if isinstance(scene_data, dict) else []
        latest_observation = observations[0] if observations else {}

        latest_object = self._as_text(latest_observation.get("object_name")) or "unknown"
        latest_confidence = self._to_float(latest_observation.get("confidence"))
        latest_observed_at = self._as_text(latest_observation.get("observed_at")) or "unknown"

        event_lines = []
        for item in events[:3]:
            event_lines.append(
                f"- {item.get('event_at')}: {item.get('event_type')} / {item.get('summary')}"
            )
        if not event_lines:
            event_lines.append("- 无最近事件")

        zone_value = self._as_text(zone_state.get("state_value")) or "unknown"
        zone_confidence = self._to_float(zone_state.get("state_confidence"))
        zone_fresh_until = self._as_text(zone_state.get("fresh_until")) or "unknown"
        zone_is_stale = bool(zone_state.get("is_stale", 0))
        scene_summary = scene.get("summary", "")

        freshness_level = self._as_text(zone_state.get("freshness_level")) or "unknown"
        uncertainty = "较高" if zone_is_stale else "低"
        parts = [
            "当前环境结构化结论",
            f"问题: {question}",
            f"结论: {zone_id} 当前状态为 {zone_value}，最新目标为 {latest_object}。",
            f"依据: zone_state={zone_value} / latest_object={latest_object} / summary={scene_summary}",
            f"证据时间: {latest_observed_at}",
            f"新鲜度: level={freshness_level} / fresh_until={zone_fresh_until} / is_stale={zone_is_stale}",
            f"不确定性: {uncertainty}",
            "调用链: take_snapshot -> describe_scene",
            f"设备: {device_id} / {camera_id} / {zone_id}",
            f"实时快照: media_id={snapshot_media_id or 'unknown'} uri={snapshot_uri or 'unavailable'}",
            f"场景描述: 区域状态={zone_value}，最新目标={latest_object}，最新置信度={self._format_conf(latest_confidence)}。",
            f"状态证据: summary={scene_summary} / fresh_until={zone_fresh_until} / is_stale={zone_is_stale} / state_confidence={self._format_conf(zone_confidence)}",
            f"最新观察: object={latest_object} / confidence={self._format_conf(latest_confidence)} / observed_at={latest_observed_at}",
            "最近事件:",
            "\n".join(event_lines),
        ]
        if snapshot_warning:
            parts.insert(10, f"抓拍状态: {snapshot_warning}")
        return "\n".join(parts)

    def _build_world_event_summary(self, *, question: str, trace_id: str, user_id: str | None) -> str:
        world = self._call_tool(
            "get_world_state",
            {"camera_id": self._default_camera_id(), "trace_id": trace_id},
            user_id=user_id,
        )
        recent_events = self._call_tool(
            "query_recent_events",
            {"limit": 3, "trace_id": trace_id},
            user_id=user_id,
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
        latest_event_at = self._as_text(events[0].get("event_at")) if events else "unknown"
        conclusion = "最近有事件更新" if events else "最近没有新的事件记录"
        uncertainty = "中" if events else "较高"
        return (
            "当前环境结构化结论\n"
            f"问题: {question}\n"
            f"结论: {conclusion}\n"
            f"依据: world_summary={summary}\n"
            f"证据时间: {latest_event_at}\n"
            "新鲜度: 依据 recent events 时间窗口\n"
            f"不确定性: {uncertainty}\n"
            "调用链: get_world_state -> query_recent_events\n"
            f"当前条目数: {world_rows}\n"
            f"最近事件:\n{timeline}"
        )

    def _handle_recent_events_text_query(
        self,
        *,
        inbound: TelegramInboundMessage,
        trace_id: str,
        question: str,
    ) -> str:
        zone_id = self._resolve_zone_id_from_question(question) or self._default_zone_id()
        result = self._call_tool(
            "query_recent_events",
            {"zone_id": zone_id, "limit": 5, "trace_id": trace_id},
            user_id=inbound.from_user_id,
        )
        events = result.get("data", [])
        latest_event_at = self._as_text(events[0].get("event_at")) if events else "unknown"
        conclusion = f"最近查询到 {len(events)} 条事件" if events else "最近没有匹配事件"
        basis = f"zone_id={zone_id or 'all'}"
        uncertainty = "中" if events else "较高"
        lines = []
        for item in events[:3]:
            lines.append(f"- {item.get('event_at')}: {item.get('event_type')} / {item.get('summary')}")
        timeline = "\n".join(lines) if lines else "- 无最近事件"
        return (
            "当前环境结构化结论\n"
            f"问题: {question}\n"
            f"结论: {conclusion}\n"
            f"依据: {basis}\n"
            f"证据时间: {latest_event_at}\n"
            "新鲜度: 依据 recent events 时间窗口\n"
            f"不确定性: {uncertainty}\n"
            "调用链: query_recent_events\n"
            f"事件时间线:\n{timeline}"
        )

    def _handle_last_seen_text_query(
        self,
        *,
        inbound: TelegramInboundMessage,
        trace_id: str,
        question: str,
    ) -> str:
        object_name = self._resolve_object_name_from_question(question)
        if not object_name:
            return "当前环境结构化结论\n结论: 未识别到目标物体，请补充对象名（例如 package/快递）。"
        camera_id = self._default_camera_id()
        zone_id = self._resolve_zone_id_from_question(question) or self._default_zone_id()
        last_seen = self._call_tool(
            "last_seen_object",
            {
                "object_name": object_name,
                "camera_id": camera_id,
                "zone_id": zone_id,
                "trace_id": trace_id,
            },
            user_id=inbound.from_user_id,
        ).get("data", {})
        staleness = self._call_tool(
            "evaluate_staleness",
            {
                "object_name": object_name,
                "camera_id": self._as_text(last_seen.get("camera_id")) or camera_id,
                "zone_id": self._as_text(last_seen.get("zone_id")) or zone_id,
                "query_text": question,
                "query_type": "last_seen",
                "trace_id": trace_id,
            },
            user_id=inbound.from_user_id,
        ).get("data", {})
        observed_at = self._as_text(last_seen.get("observed_at")) or "unknown"
        stale = bool(staleness.get("is_stale", False))
        conclusion = (
            f"{object_name} 最后一次出现在 {last_seen.get('zone_id') or 'unknown'}"
            + ("，但证据已过期" if stale else "，证据仍可用")
        )
        return (
            "当前环境结构化结论\n"
            f"问题: {question}\n"
            f"结论: {conclusion}\n"
            f"依据: camera_id={last_seen.get('camera_id')} / zone_id={last_seen.get('zone_id')}\n"
            f"证据时间: {observed_at}\n"
            f"新鲜度: level={staleness.get('freshness_level')} / fresh_until={staleness.get('fresh_until')} / is_stale={stale}\n"
            f"不确定性: {'较高' if stale else '低'}\n"
            "调用链: last_seen_object -> evaluate_staleness"
        )

    def _handle_object_state_text_query(
        self,
        *,
        inbound: TelegramInboundMessage,
        trace_id: str,
        question: str,
    ) -> str:
        object_name = self._resolve_object_name_from_question(question)
        if not object_name:
            return "当前环境结构化结论\n结论: 未识别到目标物体，请补充对象名（例如 package/快递）。"
        camera_id = self._default_camera_id()
        zone_id = self._resolve_zone_id_from_question(question) or self._default_zone_id()
        state = self._call_tool(
            "get_object_state",
            {
                "object_name": object_name,
                "camera_id": camera_id,
                "zone_id": zone_id,
                "trace_id": trace_id,
            },
            user_id=inbound.from_user_id,
        ).get("data", {})
        staleness = self._call_tool(
            "evaluate_staleness",
            {
                "object_name": object_name,
                "camera_id": camera_id,
                "zone_id": zone_id,
                "query_text": question,
                "query_type": "object_state",
                "trace_id": trace_id,
            },
            user_id=inbound.from_user_id,
        ).get("data", {})
        state_value = self._as_text(state.get("state_value")) or "unknown"
        stale = bool(staleness.get("is_stale", False))
        fallback_required = bool(staleness.get("fallback_required", False))
        conclusion = f"{object_name} 当前状态倾向 {state_value}"
        if stale or fallback_required:
            conclusion += "（建议立即复核）"
        return (
            "当前环境结构化结论\n"
            f"问题: {question}\n"
            f"结论: {conclusion}\n"
            f"依据: reason_code={state.get('reason_code')} / state_confidence={self._format_conf(self._to_float(state.get('state_confidence')))}\n"
            f"证据时间: {state.get('observed_at') or 'unknown'}\n"
            f"新鲜度: level={staleness.get('freshness_level')} / fresh_until={staleness.get('fresh_until')} / is_stale={stale} / fallback_required={fallback_required}\n"
            f"不确定性: {'较高' if stale or fallback_required else '中'}\n"
            "调用链: get_object_state -> evaluate_staleness"
        )

    def _handle_zone_state_text_query(
        self,
        *,
        inbound: TelegramInboundMessage,
        trace_id: str,
        question: str,
    ) -> str:
        camera_id = self._default_camera_id() or "cam-entry-01"
        zone_id = self._resolve_zone_id_from_question(question) or self._default_zone_id() or "entry_door"
        state = self._call_tool(
            "get_zone_state",
            {"camera_id": camera_id, "zone_id": zone_id, "trace_id": trace_id},
            user_id=inbound.from_user_id,
        ).get("data", {})
        stale = bool(state.get("is_stale", 0))
        return (
            "当前环境结构化结论\n"
            f"问题: {question}\n"
            f"结论: 区域 {zone_id} 当前状态为 {state.get('state_value')}\n"
            f"依据: reason_code={state.get('reason_code')} / evidence_count={state.get('evidence_count')}\n"
            f"证据时间: {state.get('observed_at') or 'unknown'}\n"
            f"新鲜度: level={state.get('freshness_level')} / fresh_until={state.get('fresh_until')} / is_stale={stale}\n"
            f"不确定性: {'较高' if stale else '中'}\n"
            "调用链: get_zone_state"
        )

    def _resolve_zone_id(self, *, camera_id: str, trace_id: str, user_id: str | None) -> str | None:
        world = self._call_tool(
            "get_world_state",
            {"camera_id": camera_id, "trace_id": trace_id},
            user_id=user_id,
        )
        rows = world.get("data", {}).get("items", [])
        if not isinstance(rows, list):
            return None
        for row in rows:
            if not isinstance(row, dict):
                continue
            zone_id = self._as_text(row.get("zone_id"))
            if zone_id:
                return zone_id
        return None

    @classmethod
    def _should_use_scene_flow(cls, question: str) -> bool:
        if not question:
            return False
        normalized = question.lower()
        return any(token in normalized for token in cls._SCENE_KEYWORDS)

    @classmethod
    def _detect_text_intent(cls, question: str) -> str:
        normalized = question.lower()
        if any(token in normalized for token in cls._LAST_SEEN_KEYWORDS):
            return "last_seen"
        if any(token in normalized for token in cls._OBJECT_STATE_KEYWORDS):
            return "object_state"
        if any(token in normalized for token in cls._HISTORY_KEYWORDS):
            return "history"
        if cls._should_use_scene_flow(question):
            return "scene"
        if any(token in normalized for token in cls._ZONE_STATE_KEYWORDS):
            return "zone_state"
        return "world"

    def _resolve_object_name_from_question(self, question: str) -> str | None:
        normalized = question.lower()
        alias_cfg = self._config.aliases if isinstance(self._config.aliases, dict) else {}
        object_aliases = alias_cfg.get("objects", {}) if isinstance(alias_cfg.get("objects"), dict) else {}
        for raw_name, raw_aliases in object_aliases.items():
            canonical = self._as_text(raw_name)
            aliases = raw_aliases if isinstance(raw_aliases, list) else []
            candidates = [canonical] if canonical else []
            candidates.extend(self._as_text(item) for item in aliases)
            for candidate in candidates:
                if candidate and candidate.lower() in normalized:
                    return self._as_text(aliases[0]) or canonical
        for default_token in ("package", "person", "cup", "key"):
            if default_token in normalized:
                return default_token
        return None

    def _resolve_zone_id_from_question(self, question: str) -> str | None:
        normalized = question.lower()
        alias_cfg = self._config.aliases if isinstance(self._config.aliases, dict) else {}
        zone_aliases = alias_cfg.get("zones", {}) if isinstance(alias_cfg.get("zones"), dict) else {}
        for raw_alias, raw_zone_id in zone_aliases.items():
            alias = self._as_text(raw_alias)
            zone_id = self._as_text(raw_zone_id)
            if alias and alias.lower() in normalized and zone_id:
                return zone_id
        return None

    @staticmethod
    def _to_float(value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _format_conf(value: float | None) -> str:
        if value is None:
            return "unknown"
        return f"{value:.2f}"

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
