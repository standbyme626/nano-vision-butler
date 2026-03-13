"""Unified config loader for Vision Butler v5.

Loads settings/policies/access/devices/cameras/aliases once and provides
validated config objects for app/services dependency injection.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Mapping

import yaml


class ConfigError(ValueError):
    """Raised when config file or required field is missing/invalid."""


@dataclass(frozen=True)
class AppConfig:
    settings: Dict[str, Any]
    policies: Dict[str, Any]
    access: Dict[str, Any]
    devices: Dict[str, Any]
    cameras: Dict[str, Any]
    aliases: Dict[str, Any]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "settings": self.settings,
            "policies": self.policies,
            "access": self.access,
            "devices": self.devices,
            "cameras": self.cameras,
            "aliases": self.aliases,
        }


REQUIRED_FILES = {
    "settings": "settings.yaml",
    "policies": "policies.yaml",
    "access": "access.yaml",
    "devices": "devices.yaml",
    "cameras": "cameras.yaml",
    "aliases": "aliases.yaml",
}

# Dot-path required keys per config file.
REQUIRED_FIELDS = {
    "settings": [
        "app.name",
        "app.environment",
        "runtime.entrypoint",
        "telegram.bot_token",
        "nanobot.base_url",
        "mcp.server_url",
        "database.path",
    ],
    "policies": [
        "freshness.default_ttl_sec",
        "fallback.enable_recheck_snapshot",
        "security.audit_sensitive_actions",
    ],
    "access": [
        "default_role",
        "roles",
        "telegram_allowlist.user_ids",
        "device_allowlist.device_ids",
    ],
    "devices": ["devices"],
    "cameras": ["cameras"],
    "aliases": ["objects", "zones"],
}


def _read_yaml(file_path: Path) -> Dict[str, Any]:
    if not file_path.exists():
        raise ConfigError(f"Missing config file: {file_path}")

    try:
        raw = yaml.safe_load(file_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid YAML in {file_path}: {exc}") from exc

    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ConfigError(f"Top-level object in {file_path} must be a mapping")
    return raw


def _require_field(data: Mapping[str, Any], field_path: str, file_name: str) -> None:
    cursor: Any = data
    for segment in field_path.split("."):
        if not isinstance(cursor, Mapping) or segment not in cursor:
            raise ConfigError(
                f"Missing required field '{field_path}' in config/{file_name}"
            )
        cursor = cursor[segment]
    if cursor is None:
        raise ConfigError(
            f"Required field '{field_path}' in config/{file_name} must not be null"
        )


def _validate_payload(name: str, payload: Dict[str, Any]) -> None:
    file_name = REQUIRED_FILES[name]
    for field in REQUIRED_FIELDS[name]:
        _require_field(payload, field, file_name)

    if name == "devices" and not isinstance(payload.get("devices"), list):
        raise ConfigError("Field 'devices' in config/devices.yaml must be a list")

    if name == "cameras" and not isinstance(payload.get("cameras"), list):
        raise ConfigError("Field 'cameras' in config/cameras.yaml must be a list")


def load_settings(config_dir: str | Path = "config") -> AppConfig:
    base = Path(config_dir)
    loaded: Dict[str, Dict[str, Any]] = {}

    for name, file_name in REQUIRED_FILES.items():
        payload = _read_yaml(base / file_name)
        _validate_payload(name, payload)
        loaded[name] = payload

    return AppConfig(
        settings=loaded["settings"],
        policies=loaded["policies"],
        access=loaded["access"],
        devices=loaded["devices"],
        cameras=loaded["cameras"],
        aliases=loaded["aliases"],
    )


@lru_cache(maxsize=1)
def get_settings(config_dir: str = "config") -> AppConfig:
    """Cached accessor for app/service dependency injection."""

    return load_settings(config_dir)


def clear_settings_cache() -> None:
    get_settings.cache_clear()


if __name__ == "__main__":
    cfg = load_settings()
    print(
        "Loaded config:",
        {
            "app": cfg.settings["app"]["name"],
            "env": cfg.settings["app"]["environment"],
            "devices": len(cfg.devices.get("devices", [])),
            "cameras": len(cfg.cameras.get("cameras", [])),
        },
    )
