"""Notification rule evaluation and dispatch decisions."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from src.db.repositories.audit_repo import AuditRepo
from src.db.repositories.notification_rule_repo import NotificationRuleRepo
from src.db.session import normalize_iso8601, utc_now_iso8601
from src.schemas.memory import Event
from src.schemas.security import AuditLog
from src.settings import AppConfig


class NotificationService:
    """Evaluate event-triggered notification rules with cooldown and rate limit."""

    def __init__(
        self,
        *,
        notification_rule_repo: NotificationRuleRepo,
        audit_repo: AuditRepo,
        config: AppConfig,
    ) -> None:
        self._notification_rule_repo = notification_rule_repo
        self._audit_repo = audit_repo
        self._config = config

    def evaluate_event_notifications(self, *, event: Event, trace_id: str | None = None) -> dict[str, Any]:
        rules = self._notification_rule_repo.list_active_rules(trigger_type="event")
        now_iso = utc_now_iso8601()
        now_dt = datetime.fromisoformat(now_iso.replace("Z", "+00:00")).astimezone(timezone.utc)
        notifications_cfg = self._config.policies.get("notifications", {})
        default_cooldown_sec = max(int(notifications_cfg.get("default_cooldown_sec", 60)), 0)
        max_per_hour = max(int(notifications_cfg.get("max_per_hour", 30)), 1)
        hourly_window_start = (now_dt - timedelta(hours=1)).isoformat(timespec="milliseconds").replace("+00:00", "Z")

        triggered: list[dict[str, Any]] = []
        skipped: list[dict[str, Any]] = []
        for rule in rules:
            rule_id = str(rule.get("id") or "").strip()
            user_id = str(rule.get("user_id") or "").strip()
            rule_name = str(rule.get("rule_name") or "").strip() or rule_id
            if not rule_id or not user_id:
                continue

            condition_raw = str(rule.get("condition_json") or "{}")
            try:
                condition = self._parse_condition(condition_raw)
            except ValueError:
                self._audit_decision(
                    decision="deny",
                    reason="invalid_condition_json",
                    rule_id=rule_id,
                    user_id=user_id,
                    trace_id=trace_id,
                    meta={"rule_name": rule_name, "condition_json": condition_raw, "event_id": event.id},
                )
                skipped.append(
                    {
                        "rule_id": rule_id,
                        "rule_name": rule_name,
                        "reason": "invalid_condition_json",
                    }
                )
                continue

            matched, mismatch_reason = self._match_event(event=event, condition=condition)
            if not matched:
                skipped.append({"rule_id": rule_id, "rule_name": rule_name, "reason": mismatch_reason})
                continue

            cooldown_sec = self._resolve_cooldown_sec(rule.get("cooldown_sec"), default_cooldown_sec)
            last_triggered_at = self._as_text(rule.get("last_triggered_at"))
            if self._is_cooldown_active(last_triggered_at=last_triggered_at, now_dt=now_dt, cooldown_sec=cooldown_sec):
                self._audit_decision(
                    decision="deny",
                    reason="cooldown_active",
                    rule_id=rule_id,
                    user_id=user_id,
                    trace_id=trace_id,
                    meta={
                        "rule_name": rule_name,
                        "event_id": event.id,
                        "cooldown_sec": cooldown_sec,
                        "last_triggered_at": last_triggered_at,
                    },
                )
                skipped.append({"rule_id": rule_id, "rule_name": rule_name, "reason": "cooldown_active"})
                continue

            triggered_in_last_hour = self._notification_rule_repo.count_user_triggers_since(
                user_id=user_id,
                since=hourly_window_start,
            )
            if triggered_in_last_hour >= max_per_hour:
                self._audit_decision(
                    decision="deny",
                    reason="rate_limited",
                    rule_id=rule_id,
                    user_id=user_id,
                    trace_id=trace_id,
                    meta={
                        "rule_name": rule_name,
                        "event_id": event.id,
                        "max_per_hour": max_per_hour,
                        "triggered_in_last_hour": triggered_in_last_hour,
                    },
                )
                skipped.append({"rule_id": rule_id, "rule_name": rule_name, "reason": "rate_limited"})
                continue

            message = self._build_message(rule_name=rule_name, event=event, condition=condition)
            delivery = {
                "rule_id": rule_id,
                "rule_name": rule_name,
                "user_id": user_id,
                "telegram_chat_id": self._as_text(rule.get("telegram_chat_id")),
                "message": message,
                "event_id": event.id,
            }
            triggered.append(delivery)
            self._notification_rule_repo.update_last_triggered_at(rule_id=rule_id, triggered_at=now_iso)
            self._audit_decision(
                decision="allow",
                reason="rule_triggered",
                rule_id=rule_id,
                user_id=user_id,
                trace_id=trace_id,
                meta={
                    "rule_name": rule_name,
                    "event_id": event.id,
                    "telegram_chat_id": delivery["telegram_chat_id"],
                    "cooldown_sec": cooldown_sec,
                    "message": message,
                },
            )

        return {
            "requested": len(rules),
            "triggered": len(triggered),
            "skipped": len(skipped),
            "deliveries": triggered,
            "skipped_reasons": skipped,
            "evaluated_at": now_iso,
        }

    @staticmethod
    def _resolve_cooldown_sec(raw: Any, default_value: int) -> int:
        try:
            parsed = int(raw)
        except (TypeError, ValueError):
            parsed = default_value
        return max(parsed, 0)

    @staticmethod
    def _parse_condition(raw: str) -> dict[str, Any]:
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError("condition_json must be object")
        return payload

    @staticmethod
    def _as_text(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text if text else None

    @staticmethod
    def _to_int(value: Any) -> int | None:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _is_cooldown_active(self, *, last_triggered_at: str | None, now_dt: datetime, cooldown_sec: int) -> bool:
        if cooldown_sec <= 0 or not last_triggered_at:
            return False
        last_iso = normalize_iso8601(last_triggered_at, "last_triggered_at")
        last_dt = datetime.fromisoformat(last_iso.replace("Z", "+00:00")).astimezone(timezone.utc)
        return (now_dt - last_dt).total_seconds() < cooldown_sec

    def _match_event(self, *, event: Event, condition: dict[str, Any]) -> tuple[bool, str]:
        expected_event_type = self._as_text(condition.get("event_type"))
        if expected_event_type and event.event_type != expected_event_type:
            return False, "event_type_mismatch"

        expected_object_name = self._as_text(condition.get("object_name"))
        if expected_object_name and (self._as_text(event.object_name) or "") != expected_object_name:
            return False, "object_name_mismatch"

        expected_zone_id = self._as_text(condition.get("zone_id"))
        if expected_zone_id and (self._as_text(event.zone_id) or "") != expected_zone_id:
            return False, "zone_id_mismatch"

        min_importance = self._to_int(condition.get("min_importance"))
        if min_importance is not None and int(event.importance) < min_importance:
            return False, "importance_too_low"

        return True, "matched"

    def _build_message(self, *, rule_name: str, event: Event, condition: dict[str, Any]) -> str:
        custom = self._as_text(condition.get("message_template"))
        if custom:
            return custom
        return (
            f"[{rule_name}] 触发: {event.event_type} | 对象: {event.object_name or 'unknown'} | "
            f"区域: {event.zone_id or 'unknown'} | 时间: {event.event_at}"
        )

    def _audit_decision(
        self,
        *,
        decision: str,
        reason: str,
        rule_id: str,
        user_id: str,
        trace_id: str | None,
        meta: dict[str, Any],
    ) -> None:
        self._audit_repo.save_audit_log(
            AuditLog(
                id=f"audit-{uuid4().hex[:12]}",
                user_id=user_id,
                device_id=None,
                action="notification_dispatch",
                target_type="notification_rule",
                target_id=rule_id,
                decision=decision,
                reason=reason,
                trace_id=trace_id,
                meta_json=json.dumps(meta, ensure_ascii=False, sort_keys=True, default=str),
                created_at=None,
            )
        )
