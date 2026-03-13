"""Centralized security guard for access validation and audit logging."""

from __future__ import annotations

import json
from typing import Any, Mapping
from uuid import uuid4

from src.db.repositories.audit_repo import AuditRepo
from src.db.repositories.device_repo import DeviceRepo
from src.db.repositories.media_repo import MediaRepo
from src.schemas.security import AccessDecision, AuditLog
from src.security.access_policy import AccessPolicy
from src.settings import AppConfig


class SecurityViolation(ValueError):
    """Raised when access validation fails."""

    def __init__(self, reason_code: str, message: str):
        self.reason_code = reason_code
        self.message = message
        super().__init__(f"{reason_code}: {message}")


class SecurityGuard:
    """Single place for user/device/tool/resource/media authorization checks."""

    _INTERNAL_SKILLS = {"system", "internal", "backend"}

    def __init__(
        self,
        *,
        config: AppConfig,
        audit_repo: AuditRepo,
        device_repo: DeviceRepo | None = None,
        media_repo: MediaRepo | None = None,
        policy: AccessPolicy | None = None,
    ) -> None:
        self._config = config
        self._audit_repo = audit_repo
        self._device_repo = device_repo
        self._media_repo = media_repo
        self._policy = policy or AccessPolicy.from_config(config.access)
        self._device_profiles = self._build_device_profiles(config.devices)

    def validate_user_access(
        self,
        user_id: str | None,
        *,
        trace_id: str | None = None,
        action: str = "user_access",
        meta: dict[str, Any] | None = None,
    ) -> AccessDecision:
        normalized_user = self._as_text(user_id)
        if not normalized_user:
            return self._deny(
                reason_code="USER_ID_MISSING",
                message="user_id is required",
                action=action,
                trace_id=trace_id,
                target_type="user",
                target_id=None,
                user_id=None,
                device_id=None,
                meta=meta,
            )

        if not self._policy.is_user_allowed(normalized_user):
            return self._deny(
                reason_code="USER_NOT_ALLOWED",
                message=f"User not in allowlist: {normalized_user}",
                action=action,
                trace_id=trace_id,
                target_type="user",
                target_id=normalized_user,
                user_id=normalized_user,
                device_id=None,
                meta=meta,
            )

        role = self._policy.resolve_role(normalized_user)
        return self._allow(
            reason_code="USER_ALLOWED",
            action=action,
            trace_id=trace_id,
            target_type="user",
            target_id=normalized_user,
            user_id=normalized_user,
            device_id=None,
            meta={"role": role, **(meta or {})},
        )

    def validate_device_access(
        self,
        device_id: str | None,
        *,
        api_key: str | None = None,
        trace_id: str | None = None,
        action: str = "device_access",
        meta: dict[str, Any] | None = None,
    ) -> AccessDecision:
        normalized_device = self._as_text(device_id)
        if not normalized_device:
            return self._deny(
                reason_code="DEVICE_ID_MISSING",
                message="device_id is required",
                action=action,
                trace_id=trace_id,
                target_type="device",
                target_id=None,
                user_id=None,
                device_id=None,
                meta=meta,
            )

        if not self._policy.is_device_allowed(normalized_device):
            return self._deny(
                reason_code="DEVICE_NOT_ALLOWED",
                message=f"Device not in allowlist: {normalized_device}",
                action=action,
                trace_id=trace_id,
                target_type="device",
                target_id=normalized_device,
                user_id=None,
                device_id=normalized_device,
                meta=meta,
            )

        profile = self._device_profiles.get(normalized_device)
        if profile is None:
            return self._deny(
                reason_code="DEVICE_NOT_REGISTERED",
                message=f"Device not registered in config/devices.yaml: {normalized_device}",
                action=action,
                trace_id=trace_id,
                target_type="device",
                target_id=normalized_device,
                user_id=None,
                device_id=normalized_device,
                meta=meta,
            )

        expected_api_key = self._configured_device_api_key(profile)
        normalized_api_key = self._as_text(api_key)
        if expected_api_key:
            if not normalized_api_key:
                return self._deny(
                    reason_code="DEVICE_API_KEY_REQUIRED",
                    message=f"api_key required for device: {normalized_device}",
                    action=action,
                    trace_id=trace_id,
                    target_type="device",
                    target_id=normalized_device,
                    user_id=None,
                    device_id=normalized_device,
                    meta=meta,
                )
            if normalized_api_key != expected_api_key:
                return self._deny(
                    reason_code="DEVICE_API_KEY_INVALID",
                    message=f"api_key invalid for device: {normalized_device}",
                    action=action,
                    trace_id=trace_id,
                    target_type="device",
                    target_id=normalized_device,
                    user_id=None,
                    device_id=normalized_device,
                    meta=meta,
                )

        return self._allow(
            reason_code="DEVICE_ALLOWED",
            action=action,
            trace_id=trace_id,
            target_type="device",
            target_id=normalized_device,
            user_id=None,
            device_id=normalized_device,
            meta={"camera_id": self._as_text(profile.get("camera_id")), **(meta or {})},
        )

    def validate_tool_access(
        self,
        skill_name: str | None,
        tool_name: str | None,
        *,
        user_id: str | None = None,
        trace_id: str | None = None,
        action: str = "tool_access",
        meta: dict[str, Any] | None = None,
    ) -> AccessDecision:
        normalized_tool = self._as_text(tool_name)
        if not normalized_tool:
            return self._deny(
                reason_code="TOOL_NAME_MISSING",
                message="tool_name is required",
                action=action,
                trace_id=trace_id,
                target_type="tool",
                target_id=None,
                user_id=self._as_text(user_id),
                device_id=None,
                meta=meta,
            )

        normalized_skill = self._normalize_skill(skill_name)
        normalized_user = self._as_text(user_id)
        if normalized_user and not self._policy.is_user_allowed(normalized_user):
            return self._deny(
                reason_code="USER_NOT_ALLOWED",
                message=f"User not in allowlist: {normalized_user}",
                action=action,
                trace_id=trace_id,
                target_type="tool",
                target_id=normalized_tool,
                user_id=normalized_user,
                device_id=None,
                meta={"skill_name": normalized_skill, **(meta or {})},
            )

        if normalized_skill in self._INTERNAL_SKILLS:
            return self._allow(
                reason_code="INTERNAL_SKILL_BYPASS",
                action=action,
                trace_id=trace_id,
                target_type="tool",
                target_id=normalized_tool,
                user_id=normalized_user,
                device_id=None,
                meta={"skill_name": normalized_skill, **(meta or {})},
            )

        if not self._policy.has_tool_policy(normalized_skill):
            return self._deny(
                reason_code="TOOL_POLICY_MISSING",
                message=f"Tool policy missing for skill: {normalized_skill}",
                action=action,
                trace_id=trace_id,
                target_type="tool",
                target_id=normalized_tool,
                user_id=normalized_user,
                device_id=None,
                meta={"skill_name": normalized_skill, **(meta or {})},
            )

        if not self._policy.is_tool_allowed(normalized_skill, normalized_tool):
            return self._deny(
                reason_code="TOOL_NOT_ALLOWED",
                message=f"Tool not allowed for skill={normalized_skill}: {normalized_tool}",
                action=action,
                trace_id=trace_id,
                target_type="tool",
                target_id=normalized_tool,
                user_id=normalized_user,
                device_id=None,
                meta={"skill_name": normalized_skill, **(meta or {})},
            )

        return self._allow(
            reason_code="TOOL_ALLOWED",
            action=action,
            trace_id=trace_id,
            target_type="tool",
            target_id=normalized_tool,
            user_id=normalized_user,
            device_id=None,
            meta={"skill_name": normalized_skill, **(meta or {})},
        )

    def validate_resource_access(
        self,
        skill_name: str | None,
        resource_uri: str | None,
        *,
        user_id: str | None = None,
        trace_id: str | None = None,
        action: str = "resource_access",
        meta: dict[str, Any] | None = None,
    ) -> AccessDecision:
        normalized_uri = self._as_text(resource_uri)
        if not normalized_uri:
            return self._deny(
                reason_code="RESOURCE_URI_MISSING",
                message="resource_uri is required",
                action=action,
                trace_id=trace_id,
                target_type="resource",
                target_id=None,
                user_id=self._as_text(user_id),
                device_id=None,
                meta=meta,
            )

        normalized_skill = self._normalize_skill(skill_name)
        normalized_user = self._as_text(user_id)
        if normalized_user and not self._policy.is_user_allowed(normalized_user):
            return self._deny(
                reason_code="USER_NOT_ALLOWED",
                message=f"User not in allowlist: {normalized_user}",
                action=action,
                trace_id=trace_id,
                target_type="resource",
                target_id=normalized_uri,
                user_id=normalized_user,
                device_id=None,
                meta={"skill_name": normalized_skill, **(meta or {})},
            )

        if normalized_skill in self._INTERNAL_SKILLS:
            return self._allow(
                reason_code="INTERNAL_SKILL_BYPASS",
                action=action,
                trace_id=trace_id,
                target_type="resource",
                target_id=normalized_uri,
                user_id=normalized_user,
                device_id=None,
                meta={"skill_name": normalized_skill, **(meta or {})},
            )

        if not self._policy.has_resource_policy(normalized_skill):
            return self._deny(
                reason_code="RESOURCE_POLICY_MISSING",
                message=f"Resource policy missing for skill: {normalized_skill}",
                action=action,
                trace_id=trace_id,
                target_type="resource",
                target_id=normalized_uri,
                user_id=normalized_user,
                device_id=None,
                meta={"skill_name": normalized_skill, **(meta or {})},
            )

        if not self._policy.is_resource_allowed(normalized_skill, normalized_uri):
            return self._deny(
                reason_code="RESOURCE_NOT_ALLOWED",
                message=f"Resource not allowed for skill={normalized_skill}: {normalized_uri}",
                action=action,
                trace_id=trace_id,
                target_type="resource",
                target_id=normalized_uri,
                user_id=normalized_user,
                device_id=None,
                meta={"skill_name": normalized_skill, **(meta or {})},
            )

        return self._allow(
            reason_code="RESOURCE_ALLOWED",
            action=action,
            trace_id=trace_id,
            target_type="resource",
            target_id=normalized_uri,
            user_id=normalized_user,
            device_id=None,
            meta={"skill_name": normalized_skill, **(meta or {})},
        )

    def validate_media_visibility(
        self,
        user_id: str | None,
        media_id: str | None,
        *,
        trace_id: str | None = None,
        action: str = "media_access",
        meta: dict[str, Any] | None = None,
    ) -> AccessDecision:
        normalized_user = self._as_text(user_id)
        normalized_media_id = self._as_text(media_id)
        if not normalized_user:
            return self._deny(
                reason_code="USER_ID_MISSING",
                message="user_id is required for media access",
                action=action,
                trace_id=trace_id,
                target_type="media",
                target_id=normalized_media_id,
                user_id=None,
                device_id=None,
                meta=meta,
            )
        if not normalized_media_id:
            return self._deny(
                reason_code="MEDIA_ID_MISSING",
                message="media_id is required",
                action=action,
                trace_id=trace_id,
                target_type="media",
                target_id=None,
                user_id=normalized_user,
                device_id=None,
                meta=meta,
            )
        if not self._policy.is_user_allowed(normalized_user):
            return self._deny(
                reason_code="USER_NOT_ALLOWED",
                message=f"User not in allowlist: {normalized_user}",
                action=action,
                trace_id=trace_id,
                target_type="media",
                target_id=normalized_media_id,
                user_id=normalized_user,
                device_id=None,
                meta=meta,
            )
        if self._media_repo is None:
            return self._deny(
                reason_code="MEDIA_REPO_UNAVAILABLE",
                message="Media repository not configured",
                action=action,
                trace_id=trace_id,
                target_type="media",
                target_id=normalized_media_id,
                user_id=normalized_user,
                device_id=None,
                meta=meta,
            )

        media_item = self._media_repo.get_media_item(normalized_media_id)
        if media_item is None:
            return self._deny(
                reason_code="MEDIA_NOT_FOUND",
                message=f"Media not found: {normalized_media_id}",
                action=action,
                trace_id=trace_id,
                target_type="media",
                target_id=normalized_media_id,
                user_id=normalized_user,
                device_id=None,
                meta=meta,
            )

        role = self._policy.resolve_role(normalized_user)
        scope = self._as_text(media_item.visibility_scope) or "private"
        if self._policy.role_can_view_all(role):
            return self._allow(
                reason_code="MEDIA_ALLOWED",
                action=action,
                trace_id=trace_id,
                target_type="media",
                target_id=normalized_media_id,
                user_id=normalized_user,
                device_id=None,
                meta={"role": role, "visibility_scope": scope, **(meta or {})},
            )

        allowed_scopes = self._policy.allowed_media_scopes(role)
        if "*" in allowed_scopes or scope in allowed_scopes:
            return self._allow(
                reason_code="MEDIA_ALLOWED",
                action=action,
                trace_id=trace_id,
                target_type="media",
                target_id=normalized_media_id,
                user_id=normalized_user,
                device_id=None,
                meta={"role": role, "visibility_scope": scope, **(meta or {})},
            )

        return self._deny(
            reason_code="MEDIA_SCOPE_DENIED",
            message=f"Media scope denied for role={role}: {scope}",
            action=action,
            trace_id=trace_id,
            target_type="media",
            target_id=normalized_media_id,
            user_id=normalized_user,
            device_id=None,
            meta={"role": role, "visibility_scope": scope, **(meta or {})},
        )

    def _allow(
        self,
        *,
        reason_code: str,
        action: str,
        trace_id: str | None,
        target_type: str | None,
        target_id: str | None,
        user_id: str | None,
        device_id: str | None,
        meta: dict[str, Any] | None,
    ) -> AccessDecision:
        return AccessDecision(
            allowed=True,
            reason_code=reason_code,
            message="allow",
            trace_id=trace_id,
            target_type=target_type,
            target_id=target_id,
            user_id=user_id,
            device_id=device_id,
            meta=meta or {},
        )

    def _deny(
        self,
        *,
        reason_code: str,
        message: str,
        action: str,
        trace_id: str | None,
        target_type: str | None,
        target_id: str | None,
        user_id: str | None,
        device_id: str | None,
        meta: dict[str, Any] | None,
    ) -> AccessDecision:
        decision = AccessDecision(
            allowed=False,
            reason_code=reason_code,
            message=message,
            trace_id=trace_id,
            target_type=target_type,
            target_id=target_id,
            user_id=user_id,
            device_id=device_id,
            meta=meta or {},
        )
        self.audit_deny(action=action, decision=decision)
        raise SecurityViolation(reason_code, message)

    def audit_allow(self, *, action: str, decision: AccessDecision) -> None:
        self._write_audit(action=action, decision="allow", reason=decision.reason_code, access_decision=decision, force_commit=False)

    def audit_deny(self, *, action: str, decision: AccessDecision) -> None:
        self._write_audit(action=action, decision="deny", reason=decision.reason_code, access_decision=decision, force_commit=True)

    def _write_audit(
        self,
        *,
        action: str,
        decision: str,
        reason: str,
        access_decision: AccessDecision,
        force_commit: bool,
    ) -> None:
        payload = {
            "allowed": access_decision.allowed,
            "reason_code": access_decision.reason_code,
            "message": access_decision.message,
            "raw_user_id": access_decision.user_id,
            "raw_device_id": access_decision.device_id,
            "meta": access_decision.meta,
        }
        audit_user_id = self._resolve_audit_user_id(access_decision.user_id)
        audit_device_id = self._resolve_audit_device_id(access_decision.device_id)
        self._audit_repo.save_audit_log(
            AuditLog(
                id=f"audit-{uuid4().hex[:12]}",
                user_id=audit_user_id,
                device_id=audit_device_id,
                action=action,
                target_type=access_decision.target_type,
                target_id=access_decision.target_id,
                decision=decision,
                reason=reason,
                trace_id=access_decision.trace_id,
                meta_json=json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str),
                created_at=None,
            )
        )
        if force_commit:
            try:
                self._audit_repo.conn.commit()
            except Exception:
                # Best effort: never mask original authorization denial.
                pass

    def _resolve_audit_user_id(self, user_id: str | None) -> str | None:
        normalized = self._as_text(user_id)
        if not normalized:
            return None
        row = self._audit_repo.conn.execute(
            "SELECT id FROM users WHERE id = ? LIMIT 1",
            (normalized,),
        ).fetchone()
        return normalized if row else None

    def _resolve_audit_device_id(self, device_id: str | None) -> str | None:
        normalized = self._as_text(device_id)
        if not normalized:
            return None
        if self._device_repo is not None and self._device_repo.get_device_status(normalized) is not None:
            return normalized
        row = self._audit_repo.conn.execute(
            "SELECT device_id FROM devices WHERE device_id = ? LIMIT 1",
            (normalized,),
        ).fetchone()
        return normalized if row else None

    @staticmethod
    def _as_text(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text if text else None

    @staticmethod
    def _normalize_skill(skill_name: str | None) -> str:
        normalized = str(skill_name or "system").strip()
        return normalized if normalized else "system"

    @staticmethod
    def _build_device_profiles(devices_config: Mapping[str, Any] | None) -> dict[str, dict[str, Any]]:
        devices = devices_config.get("devices", []) if isinstance(devices_config, Mapping) else []
        profiles: dict[str, dict[str, Any]] = {}
        if not isinstance(devices, list):
            return profiles
        for item in devices:
            if not isinstance(item, Mapping):
                continue
            device_id = str(item.get("device_id") or "").strip()
            if device_id:
                profiles[device_id] = dict(item)
        return profiles

    @staticmethod
    def _configured_device_api_key(profile: Mapping[str, Any]) -> str | None:
        auth = profile.get("auth") if isinstance(profile.get("auth"), Mapping) else {}
        configured = str(auth.get("api_key") or "").strip()
        if not configured or configured.startswith("__SET_"):
            return None
        return configured
