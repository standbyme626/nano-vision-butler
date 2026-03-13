"""Static registry for first-party skills introduced in T10."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SkillRegistration:
    name: str
    prompt_name: str
    skill_markdown_path: str
    allowed_tools: tuple[str, ...]


SKILL_REGISTRY: dict[str, SkillRegistration] = {
    "scene_query": SkillRegistration(
        name="scene_query",
        prompt_name="scene_query",
        skill_markdown_path="skills/scene_query/SKILL.md",
        allowed_tools=("describe_scene", "get_world_state", "take_snapshot", "evaluate_staleness"),
    ),
    "history_query": SkillRegistration(
        name="history_query",
        prompt_name="history_query",
        skill_markdown_path="skills/history_query/SKILL.md",
        allowed_tools=("query_recent_events", "get_world_state"),
    ),
    "last_seen": SkillRegistration(
        name="last_seen",
        prompt_name="last_seen_query",
        skill_markdown_path="skills/last_seen/SKILL.md",
        allowed_tools=("last_seen_object", "evaluate_staleness", "take_snapshot"),
    ),
    "object_state": SkillRegistration(
        name="object_state",
        prompt_name="object_state_query",
        skill_markdown_path="skills/object_state/SKILL.md",
        allowed_tools=("get_object_state", "evaluate_staleness", "last_seen_object", "take_snapshot"),
    ),
    "zone_state": SkillRegistration(
        name="zone_state",
        prompt_name="zone_state_query",
        skill_markdown_path="skills/zone_state/SKILL.md",
        allowed_tools=("get_zone_state", "describe_scene", "get_world_state", "take_snapshot"),
    ),
    "ocr_query": SkillRegistration(
        name="ocr_query",
        prompt_name="ocr_query",
        skill_markdown_path="skills/ocr_query/SKILL.md",
        allowed_tools=("ocr_quick_read", "ocr_extract_fields", "take_snapshot"),
    ),
    "device_status": SkillRegistration(
        name="device_status",
        prompt_name="device_status_query",
        skill_markdown_path="skills/device_status/SKILL.md",
        allowed_tools=("device_status", "take_snapshot", "get_recent_clip"),
    ),
}


def list_skills() -> list[SkillRegistration]:
    return [SKILL_REGISTRY[name] for name in sorted(SKILL_REGISTRY)]


def resolve_skill_file(repo_root: Path, skill_name: str) -> Path:
    registration = SKILL_REGISTRY[skill_name]
    return repo_root / registration.skill_markdown_path
