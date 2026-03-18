from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import yaml

from src.db.repositories.device_repo import DeviceRepo
from src.db.repositories.event_repo import EventRepo
from src.db.repositories.observation_repo import ObservationRepo
from src.db.session import utc_now_iso8601
from src.mcp_server.server import create_server
from src.schemas.device import DeviceStatus
from src.schemas.memory import Event, Observation


class MCPToolsIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory(prefix="vision_butler_t9_mcp_")
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
                content["database"]["path"] = str(Path(self.tmp_dir.name) / "mcp_test.db")
            (self.config_dir / name).write_text(
                yaml.safe_dump(content, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )

        self.server = create_server(config_dir=self.config_dir)
        with self.server.runtime.services() as svc:
            device = DeviceRepo(svc.device_repo.conn).save_device_status(
                DeviceStatus(
                    id="dev-mcp-1",
                    device_id="rk3566-dev-01",
                    camera_id="cam-entry-01",
                    device_name="rk3566-front",
                    api_key_hash="hash",
                    status="online",
                    ip_addr="127.0.0.1",
                    firmware_version="v1",
                    model_version="m1",
                    temperature=35.0,
                    cpu_load=0.2,
                    npu_load=0.1,
                    free_mem_mb=1000,
                    camera_fps=10,
                    last_seen=utc_now_iso8601(),
                    created_at=None,
                    updated_at=None,
                )
            )
            obs = ObservationRepo(svc.observation_repo.conn).save_observation(
                Observation(
                    id="obs-mcp-1",
                    device_id=device.device_id,
                    camera_id=device.camera_id,
                    zone_id="entry_door",
                    object_name="package",
                    object_class="parcel",
                    track_id=None,
                    confidence=0.95,
                    state_hint="present",
                    observed_at=utc_now_iso8601(),
                    fresh_until=utc_now_iso8601(),
                    source_event_id=None,
                    snapshot_uri=None,
                    clip_uri=None,
                    ocr_text=None,
                    visibility_scope="private",
                    raw_payload_json='{"seed":"mcp"}',
                    created_at=None,
                )
            )
            EventRepo(svc.event_repo.conn).save_event(
                Event(
                    id="evt-mcp-1",
                    observation_id=obs.id,
                    event_type="security_alert",
                    category="event",
                    importance=5,
                    camera_id=obs.camera_id,
                    zone_id=obs.zone_id,
                    object_name=obs.object_name,
                    summary="package detected at entry",
                    payload_json=None,
                    event_at=utc_now_iso8601(),
                    created_at=None,
                )
            )

    def tearDown(self) -> None:
        self.tmp_dir.cleanup()

    def test_tools_enumerate_and_call(self) -> None:
        tool_names = {item["name"] for item in self.server.list_tools()}
        self.assertIn("take_snapshot", tool_names)
        self.assertIn("evaluate_staleness", tool_names)
        self.assertIn("ocr_extract_fields", tool_names)
        self.assertIn("refresh_object_state", tool_names)
        self.assertIn("refresh_zone_state", tool_names)
        self.assertIn("audit_recent_access", tool_names)

        snapshot = self.server.call_tool("take_snapshot", {"device_id": "rk3566-dev-01", "trace_id": "t9-1"})
        self.assertTrue(snapshot["ok"])
        media_id = snapshot["data"]["media_id"]

        ocr = self.server.call_tool(
            "ocr_extract_fields",
            {
                "media_id": media_id,
                "field_schema": {"name": "string", "zone": "string"},
                "mock_raw_text": "name: parcel, zone: entry_door",
                "trace_id": "t9-ocr-1",
            },
        )
        self.assertTrue(ocr["ok"])
        self.assertEqual(ocr["data"]["fields_json"]["zone"], "entry_door")

        stale = self.server.call_tool(
            "evaluate_staleness",
            {
                "object_name": "package",
                "camera_id": "cam-entry-01",
                "zone_id": "entry_door",
                "query_type": "recent",
                "trace_id": "t9-stale-1",
            },
        )
        self.assertTrue(stale["ok"])
        self.assertIn("is_stale", stale["data"])
        self.assertIn("fallback_required", stale["data"])
        self.assertIn("freshness_level", stale["data"])

        refreshed_object = self.server.call_tool(
            "refresh_object_state",
            {
                "object_name": "package",
                "camera_id": "cam-entry-01",
                "zone_id": "entry_door",
                "trace_id": "t9-refresh-object-1",
            },
        )
        self.assertTrue(refreshed_object["ok"])
        self.assertIn("reason_code", refreshed_object["data"])

        refreshed_zone = self.server.call_tool(
            "refresh_zone_state",
            {
                "camera_id": "cam-entry-01",
                "zone_id": "entry_door",
                "trace_id": "t9-refresh-zone-1",
            },
        )
        self.assertTrue(refreshed_zone["ok"])
        self.assertIn("reason_code", refreshed_zone["data"])

        recent_audit = self.server.call_tool(
            "audit_recent_access",
            {"limit": 10, "trace_id": "t9-audit-1"},
        )
        self.assertTrue(recent_audit["ok"])
        self.assertIn("items", recent_audit["data"])
        self.assertIsInstance(recent_audit["data"]["items"], list)

    def test_resources_and_prompts_available(self) -> None:
        resource_uris = {item["uri"] for item in self.server.list_resources()}
        self.assertIn("resource://memory/events", resource_uris)
        self.assertIn("resource://policy/freshness", resource_uris)
        self.assertIn("resource://security/access_scope", resource_uris)

        events = self.server.read_resource("resource://memory/events", {"zone_id": "entry_door", "limit": 5})
        self.assertTrue(events["ok"])
        self.assertGreaterEqual(len(events["data"]["items"]), 1)

        access_scope = self.server.read_resource(
            "resource://security/access_scope",
            {"skill_name": "mcp_console", "user_id": "7566115125", "trace_id": "t9-scope-1"},
        )
        self.assertTrue(access_scope["ok"])
        self.assertIn("tool_allowlist_per_skill", access_scope["data"])
        self.assertIn("resource_scope_per_skill", access_scope["data"])

        prompt_names = {item["name"] for item in self.server.list_prompts()}
        self.assertIn("scene_query", prompt_names)
        self.assertIn("ocr_query", prompt_names)

        prompt = self.server.get_prompt(
            "scene_query",
            {"camera_id": "cam-entry-01", "zone_id": "entry_door", "question": "现在有人吗？"},
        )
        self.assertTrue(prompt["ok"])
        self.assertIn("cam-entry-01", prompt["data"]["rendered"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
