from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import yaml

from src.db.repositories.audit_repo import AuditRepo
from src.db.repositories.device_repo import DeviceRepo
from src.db.repositories.media_repo import MediaRepo
from src.db.session import SQLiteSessionFactory, create_connection, initialize_database
from src.schemas.memory import MediaItem
from src.security.security_guard import SecurityGuard, SecurityViolation
from src.settings import load_settings


class SecurityGuardUnitTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory(prefix="vision_butler_t14_guard_")
        self.config_dir = Path(self.tmp_dir.name) / "config"
        self.config_dir.mkdir(parents=True, exist_ok=True)

        repo_root = Path(__file__).resolve().parents[2]
        source_config = repo_root / "config"
        for name in [
            "settings.yaml",
            "policies.yaml",
            "access.yaml",
            "devices.yaml",
            "cameras.yaml",
            "aliases.yaml",
        ]:
            content = yaml.safe_load((source_config / name).read_text(encoding="utf-8"))
            if name == "settings.yaml":
                content["database"]["path"] = str(Path(self.tmp_dir.name) / "guard_test.db")
            if name == "access.yaml":
                content["telegram_allowlist"]["user_ids"] = ["42"]
                content["user_roles"] = {"42": "viewer"}
                content["roles"]["viewer"]["can_view_all"] = False
                content["tool_allowlist_per_skill"] = {
                    "telegram": ["get_world_state"],
                    "media_skill": ["ocr_quick_read"],
                }
                content["resource_scope_per_skill"] = {
                    "audit_skill": ["resource://memory/events"],
                }
                content["media_visibility_scope"] = {
                    "viewer": ["public"],
                    "owner": ["private", "public"],
                }
            if name == "devices.yaml":
                content["devices"][0]["auth"]["api_key"] = "device-secret"
            (self.config_dir / name).write_text(
                yaml.safe_dump(content, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )

        self.config = load_settings(self.config_dir)
        db_path = Path(self.config.settings["database"]["path"])
        initialize_database(db_path=db_path, schema_path=repo_root / "schema.sql")
        self.session_factory = SQLiteSessionFactory(db_path)

    def tearDown(self) -> None:
        self.tmp_dir.cleanup()

    def _make_guard(self) -> tuple[SecurityGuard, AuditRepo, MediaRepo]:
        conn = create_connection(self.session_factory.db_path)
        self.addCleanup(conn.close)
        media_repo = MediaRepo(conn)
        guard = SecurityGuard(
            config=self.config,
            audit_repo=AuditRepo(conn),
            device_repo=DeviceRepo(conn),
            media_repo=media_repo,
        )
        return guard, AuditRepo(conn), media_repo

    def test_validate_user_access_allow_and_deny(self) -> None:
        guard, audit_repo, _ = self._make_guard()

        allow = guard.validate_user_access("42", trace_id="guard-user-allow")
        self.assertTrue(allow.allowed)
        self.assertEqual(allow.reason_code, "USER_ALLOWED")

        with self.assertRaises(SecurityViolation) as denied:
            guard.validate_user_access("99", trace_id="guard-user-deny")
        self.assertIn("USER_NOT_ALLOWED", str(denied.exception))

        rows = [
            row
            for row in audit_repo.list_recent(limit=20)
            if row.action == "user_access" and row.decision == "deny" and row.reason == "USER_NOT_ALLOWED"
        ]
        self.assertGreaterEqual(len(rows), 1)

    def test_validate_device_access_checks_allowlist_and_api_key(self) -> None:
        guard, _, _ = self._make_guard()

        allow = guard.validate_device_access(
            "rk3566-dev-01",
            api_key="device-secret",
            trace_id="guard-device-allow",
        )
        self.assertTrue(allow.allowed)

        with self.assertRaises(SecurityViolation) as invalid_key:
            guard.validate_device_access("rk3566-dev-01", api_key="bad-key", trace_id="guard-device-deny")
        self.assertIn("DEVICE_API_KEY_INVALID", str(invalid_key.exception))

        with self.assertRaises(SecurityViolation) as unknown:
            guard.validate_device_access("rogue-device", api_key="x", trace_id="guard-device-deny-2")
        self.assertIn("DEVICE_NOT_ALLOWED", str(unknown.exception))

    def test_validate_tool_and_resource_access(self) -> None:
        guard, _, _ = self._make_guard()

        allow_tool = guard.validate_tool_access(
            "telegram",
            "get_world_state",
            user_id="42",
            trace_id="guard-tool-allow",
        )
        self.assertTrue(allow_tool.allowed)

        with self.assertRaises(SecurityViolation) as denied_tool:
            guard.validate_tool_access("telegram", "take_snapshot", user_id="42", trace_id="guard-tool-deny")
        self.assertIn("TOOL_NOT_ALLOWED", str(denied_tool.exception))

        with self.assertRaises(SecurityViolation) as missing_resource_policy:
            guard.validate_resource_access(
                "unknown_skill",
                "resource://memory/events",
                user_id="42",
                trace_id="guard-resource-deny",
            )
        self.assertIn("RESOURCE_POLICY_MISSING", str(missing_resource_policy.exception))

    def test_validate_media_visibility_respects_scope(self) -> None:
        guard, _, media_repo = self._make_guard()
        media_repo.save_media_item(
            MediaItem(
                id="media-private-1",
                owner_type="manual",
                owner_id="cmd-1",
                media_type="image",
                uri="file://private.jpg",
                local_path="/tmp/private.jpg",
                mime_type="image/jpeg",
                duration_sec=None,
                width=100,
                height=100,
                visibility_scope="private",
                sha256=None,
                created_at=None,
            )
        )
        media_repo.save_media_item(
            MediaItem(
                id="media-public-1",
                owner_type="manual",
                owner_id="cmd-2",
                media_type="image",
                uri="file://public.jpg",
                local_path="/tmp/public.jpg",
                mime_type="image/jpeg",
                duration_sec=None,
                width=100,
                height=100,
                visibility_scope="public",
                sha256=None,
                created_at=None,
            )
        )

        allow_public = guard.validate_media_visibility("42", "media-public-1", trace_id="guard-media-allow")
        self.assertTrue(allow_public.allowed)

        with self.assertRaises(SecurityViolation) as denied_private:
            guard.validate_media_visibility("42", "media-private-1", trace_id="guard-media-deny")
        self.assertIn("MEDIA_SCOPE_DENIED", str(denied_private.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)
