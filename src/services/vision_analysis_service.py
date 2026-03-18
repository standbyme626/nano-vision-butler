"""Vision analysis service for slower backend multimodal passes."""

from __future__ import annotations

import base64
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from uuid import uuid4

from src.db.repositories.audit_repo import AuditRepo
from src.db.repositories.event_repo import EventRepo
from src.db.repositories.media_repo import MediaRepo
from src.db.repositories.observation_repo import ObservationRepo
from src.db.session import require_non_empty, utc_now_iso8601
from src.schemas.memory import Event, MediaItem, Observation
from src.schemas.security import AuditLog


class VisionAnalysisEngineError(RuntimeError):
    """Raised when the backend vision adapter fails."""


class StubVisionAdapter:
    """Deterministic local stub used by tests and dry runs."""

    def describe(self, image_uri: str, prompt: str, payload: dict[str, Any]) -> dict[str, Any]:
        summary = VisionAnalysisService.as_optional_text(payload.get("mock_summary"))
        if summary:
            text = summary
        else:
            parsed = urlparse(image_uri)
            candidate = Path(parsed.path).name if parsed.path else image_uri
            label = VisionAnalysisService.as_optional_text(payload.get("object_name")) or "scene"
            text = f"Stub Q8 summary for {label} from {candidate}"
        return {
            "summary": text,
            "backend": "stub",
            "model": "stub-q8",
            "prompt": prompt,
        }


class OllamaVisionAdapter:
    """Minimal Ollama chat API adapter for local Q8 multimodal calls."""

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        timeout_sec: float,
        keep_alive: str,
        temperature: float,
        num_predict: int,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout_sec = timeout_sec
        self._keep_alive = keep_alive
        self._temperature = temperature
        self._num_predict = num_predict

    def describe(self, image_uri: str, prompt: str, payload: dict[str, Any]) -> dict[str, Any]:
        image_path = self._resolve_local_path(image_uri)
        if not image_path.exists():
            raise VisionAnalysisEngineError(f"image not found: {image_path}")

        timeout_sec = VisionAnalysisService.to_float(payload.get("timeout_sec")) or self._timeout_sec
        keep_alive = VisionAnalysisService.as_optional_text(payload.get("keep_alive")) or self._keep_alive
        model = VisionAnalysisService.as_optional_text(payload.get("model")) or self._model
        with image_path.open("rb") as handle:
            image_b64 = base64.b64encode(handle.read()).decode("ascii")

        body = {
            "model": model,
            "stream": False,
            "keep_alive": keep_alive,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                    "images": [image_b64],
                }
            ],
            "options": {
                "temperature": VisionAnalysisService.to_float(payload.get("temperature")) or self._temperature,
                "num_predict": VisionAnalysisService.to_int(payload.get("num_predict")) or self._num_predict,
            },
        }
        request = Request(
            url=f"{self._base_url}/api/chat",
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=timeout_sec) as response:
                raw = response.read().decode("utf-8")
        except Exception as exc:  # pragma: no cover - network/runtime failure depends on environment
            raise VisionAnalysisEngineError(f"ollama request failed: {exc}") from exc

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:  # pragma: no cover - defensive branch
            raise VisionAnalysisEngineError("ollama returned invalid json") from exc

        message = parsed.get("message") if isinstance(parsed.get("message"), dict) else {}
        summary = VisionAnalysisService.as_optional_text(message.get("content"))
        if not summary:
            raise VisionAnalysisEngineError("ollama returned empty content")
        return {
            "summary": summary,
            "backend": "ollama",
            "model": VisionAnalysisService.as_optional_text(parsed.get("model")) or model,
            "prompt": prompt,
            "eval_count": parsed.get("eval_count"),
            "total_duration": parsed.get("total_duration"),
        }

    @staticmethod
    def _resolve_local_path(image_uri: str) -> Path:
        parsed = urlparse(image_uri)
        if parsed.scheme in {"", "file"}:
            candidate = parsed.path or image_uri
            return Path(candidate)
        raise VisionAnalysisEngineError(f"unsupported image uri: {image_uri}")


@dataclass(frozen=True)
class VisionSourceContext:
    image_uri: str
    source_media_id: str
    source_observation_id: str | None
    source_event_id: str | None
    observation: Observation | None


class VisionAnalysisService:
    """Slow backend analysis for periodic multimodal scene descriptions."""

    def __init__(
        self,
        *,
        media_repo: MediaRepo,
        observation_repo: ObservationRepo,
        event_repo: EventRepo,
        audit_repo: AuditRepo,
        adapter: StubVisionAdapter | OllamaVisionAdapter | None = None,
    ) -> None:
        self._media_repo = media_repo
        self._observation_repo = observation_repo
        self._event_repo = event_repo
        self._audit_repo = audit_repo
        self._adapter = adapter or self._build_default_adapter()

    def describe_scene(self, payload: dict[str, Any]) -> dict[str, Any]:
        trace_id = self.as_optional_text(payload.get("trace_id"))
        source = self._resolve_source(payload)
        prompt = self._build_prompt(payload=payload, observation=source.observation)
        started_at = time.monotonic()
        try:
            adapter_result = self._adapter.describe(source.image_uri, prompt, payload)
            duration_ms = round((time.monotonic() - started_at) * 1000.0, 3)
            summary = require_non_empty(self.as_optional_text(adapter_result.get("summary")), "summary")
            saved_event = self._event_repo.save_event(
                Event(
                    id=f"evt-{uuid4().hex[:12]}",
                    observation_id=source.source_observation_id,
                    event_type=self.as_optional_text(payload.get("event_type")) or "vision_q8_described",
                    category="event",
                    importance=self._normalize_importance(payload.get("importance")),
                    camera_id=(
                        self.as_optional_text(payload.get("camera_id"))
                        or (source.observation.camera_id if source.observation else None)
                    ),
                    zone_id=(
                        self.as_optional_text(payload.get("zone_id"))
                        or (source.observation.zone_id if source.observation else None)
                    ),
                    object_name=(
                        self.as_optional_text(payload.get("object_name"))
                        or (source.observation.object_name if source.observation else None)
                    ),
                    summary=summary,
                    payload_json=json.dumps(
                        {
                            "source_media_id": source.source_media_id,
                            "source_event_id": source.source_event_id,
                            "input_uri": source.image_uri,
                            "prompt": prompt,
                            "backend": self.as_optional_text(adapter_result.get("backend")),
                            "model": self.as_optional_text(adapter_result.get("model")),
                            "duration_ms": duration_ms,
                            "track_id": self.as_optional_text(payload.get("track_id")),
                            "object_class": self.as_optional_text(payload.get("object_class")),
                            "summary": summary,
                        },
                        ensure_ascii=False,
                        sort_keys=True,
                    ),
                    event_at=utc_now_iso8601(),
                    created_at=None,
                )
            )
        except (VisionAnalysisEngineError, ValueError) as exc:
            self._write_audit(
                action="vision_q8_describe",
                decision="deny",
                reason=str(exc),
                trace_id=trace_id,
                target_id=source.source_observation_id if "source" in locals() else None,
                meta={
                    "input_uri": self.as_optional_text(payload.get("input_uri")),
                    "object_name": self.as_optional_text(payload.get("object_name")),
                },
            )
            raise ValueError(f"Vision analysis failed: {exc}") from exc

        response = {
            "status": "ok",
            "backend": self.as_optional_text(adapter_result.get("backend")) or "vision_service",
            "model": self.as_optional_text(adapter_result.get("model")),
            "summary": saved_event.summary,
            "vision_event_id": saved_event.id,
            "source_media_id": source.source_media_id,
            "source_observation_id": source.source_observation_id,
            "duration_ms": duration_ms,
        }
        self._write_audit(
            action="vision_q8_describe",
            decision="allow",
            reason="analysis_saved",
            trace_id=trace_id,
            target_id=saved_event.id,
            meta=response,
        )
        return response

    def _resolve_source(self, payload: dict[str, Any]) -> VisionSourceContext:
        media_id = self.as_optional_text(payload.get("media_id"))
        input_uri = self.as_optional_text(payload.get("input_uri")) or self.as_optional_text(payload.get("image_uri"))
        observation_id = self.as_optional_text(payload.get("observation_id")) or self.as_optional_text(
            payload.get("source_observation_id")
        )
        event_id = self.as_optional_text(payload.get("event_id"))

        observation: Observation | None = None
        event: Event | None = None
        if event_id:
            event = self._event_repo.get_event(event_id)
            if event is None:
                raise ValueError(f"event_id not found: {event_id}")
            if not observation_id and event.observation_id:
                observation_id = event.observation_id

        if observation_id:
            observation = self._observation_repo.get_observation(observation_id)
            if observation is None:
                raise ValueError(f"observation_id not found: {observation_id}")

        if media_id:
            media = self._media_repo.get_media_item(media_id)
            if media is None:
                raise ValueError(f"media_id not found: {media_id}")
            image_uri = input_uri or media.uri
            return VisionSourceContext(
                image_uri=require_non_empty(image_uri, "image_uri"),
                source_media_id=media.id,
                source_observation_id=observation_id,
                source_event_id=event_id,
                observation=observation,
            )

        image_uri = require_non_empty(input_uri, "input_uri or media_id")
        persisted = self._ensure_source_media(
            image_uri=image_uri,
            observation_id=observation_id,
            event_id=event_id,
        )
        return VisionSourceContext(
            image_uri=image_uri,
            source_media_id=persisted.id,
            source_observation_id=observation_id,
            source_event_id=event_id,
            observation=observation,
        )

    def _ensure_source_media(
        self,
        *,
        image_uri: str,
        observation_id: str | None,
        event_id: str | None,
    ) -> MediaItem:
        existing = self._media_repo.get_media_item_by_uri(image_uri)
        if existing is not None:
            return existing

        parsed = urlparse(image_uri)
        local_path = parsed.path or image_uri
        suffix = Path(local_path).suffix.lower()
        mime_type = "image/png" if suffix == ".png" else "image/jpeg"
        if observation_id:
            owner_type = "observation"
            owner_id = observation_id
        elif event_id:
            owner_type = "event"
            owner_id = event_id
        else:
            owner_type = "manual"
            owner_id = f"vision-{uuid4().hex[:8]}"
        return self._media_repo.save_media_item(
            MediaItem(
                id=f"media-{uuid4().hex[:12]}",
                owner_type=owner_type,
                owner_id=owner_id,
                media_type="image",
                uri=image_uri,
                local_path=local_path,
                mime_type=mime_type,
                duration_sec=None,
                width=None,
                height=None,
                visibility_scope="private",
                sha256=None,
                created_at=None,
            )
        )

    def _build_prompt(self, *, payload: dict[str, Any], observation: Observation | None) -> str:
        prompt = self.as_optional_text(payload.get("prompt"))
        if prompt:
            return prompt
        object_name = self.as_optional_text(payload.get("object_name")) or (observation.object_name if observation else None)
        object_class = self.as_optional_text(payload.get("object_class")) or (
            observation.object_class if observation else None
        )
        zone_id = self.as_optional_text(payload.get("zone_id")) or (observation.zone_id if observation else None)
        track_id = self.as_optional_text(payload.get("track_id")) or (observation.track_id if observation else None)
        focus = object_name or object_class or "scene"
        return (
            "请用中文输出一段简洁描述，重点回答当前画面里是否有人、人在做什么、姿态和位置线索。"
            f" focus={focus}; zone={zone_id or 'unknown'}; track={track_id or 'n/a'}。"
            " 不要猜测未看到的信息。"
        )

    def _write_audit(
        self,
        *,
        action: str,
        decision: str,
        reason: str,
        trace_id: str | None,
        target_id: str | None,
        meta: dict[str, Any],
    ) -> None:
        self._audit_repo.save_audit_log(
            AuditLog(
                id=f"audit-{uuid4().hex[:12]}",
                user_id=None,
                device_id=None,
                action=action,
                target_type="event",
                target_id=target_id,
                decision=decision,
                reason=reason,
                trace_id=trace_id,
                meta_json=json.dumps(meta, ensure_ascii=False, sort_keys=True),
                created_at=utc_now_iso8601(),
            )
        )

    @staticmethod
    def _build_default_adapter() -> StubVisionAdapter | OllamaVisionAdapter:
        provider = (os.getenv("VISION_Q8_PROVIDER", "stub") or "stub").strip().lower()
        if provider == "ollama":
            return OllamaVisionAdapter(
                base_url=(os.getenv("VISION_Q8_OLLAMA_BASE_URL", "http://127.0.0.1:11434") or "http://127.0.0.1:11434"),
                model=(os.getenv("VISION_Q8_OLLAMA_MODEL", "qwen3.5:0.8b") or "qwen3.5:0.8b"),
                timeout_sec=VisionAnalysisService.to_float(os.getenv("VISION_Q8_TIMEOUT_SEC")) or 30.0,
                keep_alive=(os.getenv("VISION_Q8_KEEP_ALIVE", "5m") or "5m"),
                temperature=VisionAnalysisService.to_float(os.getenv("VISION_Q8_TEMPERATURE")) or 0.1,
                num_predict=VisionAnalysisService.to_int(os.getenv("VISION_Q8_NUM_PREDICT")) or 160,
            )
        return StubVisionAdapter()

    @staticmethod
    def _normalize_importance(value: Any) -> int:
        parsed = VisionAnalysisService.to_int(value)
        if parsed is None:
            return 3
        if parsed < 1:
            return 1
        if parsed > 5:
            return 5
        return parsed

    @staticmethod
    def as_optional_text(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def to_float(value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def to_int(value: Any) -> int | None:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
