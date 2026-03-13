"""Access policy model loaded from access/devices config."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class AccessPolicy:
    default_role: str
    user_allowlist: set[str]
    device_allowlist: set[str]
    user_roles: dict[str, str]
    role_permissions: dict[str, dict[str, bool]]
    tool_allowlist_per_skill: dict[str, set[str]]
    resource_scope_per_skill: dict[str, set[str]]
    media_visibility_scope: dict[str, set[str]]

    @classmethod
    def from_config(cls, access_config: Mapping[str, Any] | None) -> "AccessPolicy":
        payload = access_config if isinstance(access_config, Mapping) else {}

        default_role = str(payload.get("default_role") or "viewer").strip() or "viewer"
        user_allowlist = _normalize_set(payload.get("telegram_allowlist", {}).get("user_ids"))
        device_allowlist = _normalize_set(payload.get("device_allowlist", {}).get("device_ids"))

        user_roles_raw = payload.get("user_roles")
        user_roles: dict[str, str] = {}
        if isinstance(user_roles_raw, Mapping):
            for raw_user_id, raw_role in user_roles_raw.items():
                user_id = str(raw_user_id).strip()
                role = str(raw_role).strip()
                if user_id and role:
                    user_roles[user_id] = role

        role_permissions_raw = payload.get("roles")
        role_permissions: dict[str, dict[str, bool]] = {}
        if isinstance(role_permissions_raw, Mapping):
            for raw_role, perms in role_permissions_raw.items():
                role = str(raw_role).strip()
                if not role or not isinstance(perms, Mapping):
                    continue
                role_permissions[role] = {str(k): bool(v) for k, v in perms.items()}

        tool_allowlist_per_skill = _normalize_map_set(payload.get("tool_allowlist_per_skill"))
        legacy_tool_allowlist = _normalize_set(payload.get("mcp_tool_allowlist"))
        if legacy_tool_allowlist and "telegram" not in tool_allowlist_per_skill:
            tool_allowlist_per_skill["telegram"] = legacy_tool_allowlist

        resource_scope_per_skill = _normalize_map_set(payload.get("resource_scope_per_skill"))
        media_visibility_scope = _normalize_map_set(payload.get("media_visibility_scope"))

        return cls(
            default_role=default_role,
            user_allowlist=user_allowlist,
            device_allowlist=device_allowlist,
            user_roles=user_roles,
            role_permissions=role_permissions,
            tool_allowlist_per_skill=tool_allowlist_per_skill,
            resource_scope_per_skill=resource_scope_per_skill,
            media_visibility_scope=media_visibility_scope,
        )

    def resolve_role(self, user_id: str) -> str:
        return self.user_roles.get(user_id, self.default_role)

    def role_can_view_all(self, role: str) -> bool:
        perms = self.role_permissions.get(role, {})
        return bool(perms.get("can_view_all", False))

    def allowed_media_scopes(self, role: str) -> set[str]:
        return set(self.media_visibility_scope.get(role, set()))

    def is_user_allowed(self, user_id: str) -> bool:
        if not self.user_allowlist:
            return True
        return user_id in self.user_allowlist

    def is_device_allowed(self, device_id: str) -> bool:
        if not self.device_allowlist:
            return True
        return device_id in self.device_allowlist

    def has_tool_policy(self, skill_name: str) -> bool:
        return skill_name in self.tool_allowlist_per_skill

    def has_resource_policy(self, skill_name: str) -> bool:
        return skill_name in self.resource_scope_per_skill

    def is_tool_allowed(self, skill_name: str, tool_name: str) -> bool:
        allowset = self.tool_allowlist_per_skill.get(skill_name)
        if allowset is None:
            return False
        return "*" in allowset or tool_name in allowset

    def is_resource_allowed(self, skill_name: str, resource_uri: str) -> bool:
        allowset = self.resource_scope_per_skill.get(skill_name)
        if allowset is None:
            return False
        return "*" in allowset or resource_uri in allowset



def _normalize_set(value: Any) -> set[str]:
    if not isinstance(value, list):
        return set()
    result: set[str] = set()
    for item in value:
        normalized = str(item).strip()
        if normalized:
            result.add(normalized)
    return result



def _normalize_map_set(value: Any) -> dict[str, set[str]]:
    if not isinstance(value, Mapping):
        return {}
    result: dict[str, set[str]] = {}
    for raw_key, raw_values in value.items():
        key = str(raw_key).strip()
        if not key:
            continue
        result[key] = _normalize_set(raw_values)
    return result
