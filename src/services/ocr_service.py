"""OCR service with model-direct and tool-structured dual channels."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse
from uuid import uuid4

from src.db.repositories.audit_repo import AuditRepo
from src.db.repositories.event_repo import EventRepo
from src.db.repositories.media_repo import MediaRepo
from src.db.repositories.observation_repo import ObservationRepo
from src.db.repositories.ocr_repo import OcrRepo
from src.db.session import require_non_empty, utc_now_iso8601
from src.schemas.memory import Event, MediaItem, OcrResult, Observation
from src.schemas.security import AuditLog


class OCREngineError(RuntimeError):
    """Raised when OCR adapter execution fails."""


class ModelOCRAdapter:
    """Stub adapter for model-direct OCR channel."""

    def quick_read(self, image_uri: str, payload: dict[str, Any]) -> dict[str, Any]:
        if OCRService.to_bool(payload.get("simulate_failure")):
            raise OCREngineError("model adapter failed")
        raw_text = OCRService.as_optional_text(payload.get("mock_raw_text")) or self._default_text(image_uri)
        return {
            "raw_text": raw_text,
            "boxes_json": payload.get("boxes_json", []),
            "language": OCRService.as_optional_text(payload.get("language")) or "en",
            "confidence": OCRService.to_float(payload.get("confidence")) or 0.82,
        }

    @staticmethod
    def _default_text(image_uri: str) -> str:
        parsed = urlparse(image_uri)
        candidate = Path(parsed.path).name if parsed.path else image_uri
        normalized = re.sub(r"[_\-]+", " ", candidate).strip() or "image"
        return f"OCR text from {normalized}"


class ToolOCRAdapter:
    """Stub adapter for structured OCR extraction channel."""

    def extract_fields(
        self,
        image_uri: str,
        payload: dict[str, Any],
        field_schema: dict[str, Any] | list[Any] | None,
    ) -> dict[str, Any]:
        if OCRService.to_bool(payload.get("simulate_failure")):
            raise OCREngineError("tool adapter failed")

        raw_text = OCRService.as_optional_text(payload.get("mock_raw_text")) or self._default_text(image_uri)
        fields = self._extract_structured_fields(raw_text=raw_text, field_schema=field_schema)
        return {
            "raw_text": raw_text,
            "fields_json": fields,
            "boxes_json": payload.get("boxes_json", []),
            "language": OCRService.as_optional_text(payload.get("language")) or "en",
            "confidence": OCRService.to_float(payload.get("confidence")) or 0.9,
        }

    def _extract_structured_fields(
        self,
        *,
        raw_text: str,
        field_schema: dict[str, Any] | list[Any] | None,
    ) -> dict[str, Any]:
        keys = self._schema_keys(field_schema)
        if not keys:
            return self._default_fields(raw_text)

        fields: dict[str, Any] = {}
        for key in keys:
            pattern = re.compile(rf"{re.escape(key)}\s*[:=]\s*([^\n,;]+)", re.IGNORECASE)
            match = pattern.search(raw_text)
            fields[key] = match.group(1).strip() if match else None
        return fields

    @staticmethod
    def _default_text(image_uri: str) -> str:
        parsed = urlparse(image_uri)
        candidate = Path(parsed.path).name if parsed.path else image_uri
        normalized = re.sub(r"[_\-]+", " ", candidate).strip() or "image"
        return f"Structured OCR from {normalized}"

    @staticmethod
    def _schema_keys(field_schema: dict[str, Any] | list[Any] | None) -> list[str]:
        if isinstance(field_schema, dict):
            return [str(k).strip() for k in field_schema.keys() if str(k).strip()]
        if isinstance(field_schema, list):
            keys: list[str] = []
            for item in field_schema:
                if isinstance(item, str) and item.strip():
                    keys.append(item.strip())
                elif isinstance(item, dict):
                    key = OCRService.as_optional_text(item.get("name") or item.get("field"))
                    if key:
                        keys.append(key)
            return keys
        return []

    @staticmethod
    def _default_fields(raw_text: str) -> dict[str, Any]:
        amount_match = re.search(r"([0-9]+(?:\.[0-9]{2})?)", raw_text)
        date_match = re.search(r"(\d{4}[-/]\d{1,2}[-/]\d{1,2})", raw_text)
        return {
            "summary": raw_text[:120],
            "amount": amount_match.group(1) if amount_match else None,
            "date": date_match.group(1) if date_match else None,
        }


@dataclass(frozen=True)
class OCRSourceContext:
    image_uri: str
    source_media_id: str
    source_observation_id: str | None
    source_event_id: str | None


class OCRService:
    """Service boundary for OCR routes and OCR result persistence."""

    def __init__(
        self,
        *,
        media_repo: MediaRepo,
        observation_repo: ObservationRepo,
        event_repo: EventRepo,
        ocr_repo: OcrRepo,
        audit_repo: AuditRepo,
        model_adapter: ModelOCRAdapter | None = None,
        tool_adapter: ToolOCRAdapter | None = None,
    ) -> None:
        self._media_repo = media_repo
        self._observation_repo = observation_repo
        self._event_repo = event_repo
        self._ocr_repo = ocr_repo
        self._audit_repo = audit_repo
        self._model_adapter = model_adapter or ModelOCRAdapter()
        self._tool_adapter = tool_adapter or ToolOCRAdapter()

    def quick_read(self, payload: dict[str, Any]) -> dict[str, Any]:
        source = self._resolve_source(payload)
        trace_id = self.as_optional_text(payload.get("trace_id"))
        try:
            adapter_result = self._model_adapter.quick_read(source.image_uri, payload)
            saved = self.save_ocr_result(
                source_media_id=source.source_media_id,
                source_observation_id=source.source_observation_id,
                ocr_mode="model_direct",
                raw_text=self.as_optional_text(adapter_result.get("raw_text")),
                fields_json={},
                boxes_json=self._normalize_boxes(adapter_result.get("boxes_json")),
                language=self.as_optional_text(adapter_result.get("language")),
                confidence=self.to_float(adapter_result.get("confidence")),
            )
            attached_observation = self.attach_ocr_result_to_observation(
                observation_id=source.source_observation_id,
                raw_text=saved.raw_text,
            )
            promoted_event = self.promote_ocr_to_event(
                payload=payload,
                observation_id=source.source_observation_id,
                raw_text=saved.raw_text,
                fields_json={},
            )

            response = self._build_response(
                saved=saved,
                fields_json={},
                boxes_json=self._normalize_boxes(adapter_result.get("boxes_json")),
                source=source,
                attached_observation=attached_observation,
                promoted_event=promoted_event,
            )
            self._write_audit(
                action="ocr_quick_read",
                decision="allow",
                reason="ocr_completed",
                target_id=saved.id,
                trace_id=trace_id,
                meta=response,
            )
            return response
        except OCREngineError as exc:
            self._write_audit(
                action="ocr_quick_read",
                decision="deny",
                reason="ocr_failed",
                target_id=source.source_media_id,
                trace_id=trace_id,
                meta={"error": str(exc), "payload": payload},
            )
            raise ValueError(f"OCR execution failed: {exc}") from exc

    def extract_fields(self, payload: dict[str, Any]) -> dict[str, Any]:
        source = self._resolve_source(payload)
        trace_id = self.as_optional_text(payload.get("trace_id"))
        field_schema = payload.get("field_schema")
        try:
            adapter_result = self._tool_adapter.extract_fields(
                source.image_uri,
                payload,
                field_schema if isinstance(field_schema, (dict, list)) else None,
            )
            fields_json = self._normalize_fields(adapter_result.get("fields_json"))
            boxes_json = self._normalize_boxes(adapter_result.get("boxes_json"))
            saved = self.save_ocr_result(
                source_media_id=source.source_media_id,
                source_observation_id=source.source_observation_id,
                ocr_mode="tool_structured",
                raw_text=self.as_optional_text(adapter_result.get("raw_text")),
                fields_json=fields_json,
                boxes_json=boxes_json,
                language=self.as_optional_text(adapter_result.get("language")),
                confidence=self.to_float(adapter_result.get("confidence")),
            )
            attached_observation = self.attach_ocr_result_to_observation(
                observation_id=source.source_observation_id,
                raw_text=saved.raw_text,
            )
            promoted_event = self.promote_ocr_to_event(
                payload=payload,
                observation_id=source.source_observation_id,
                raw_text=saved.raw_text,
                fields_json=fields_json,
            )

            response = self._build_response(
                saved=saved,
                fields_json=fields_json,
                boxes_json=boxes_json,
                source=source,
                attached_observation=attached_observation,
                promoted_event=promoted_event,
            )
            self._write_audit(
                action="ocr_extract_fields",
                decision="allow",
                reason="ocr_completed",
                target_id=saved.id,
                trace_id=trace_id,
                meta=response,
            )
            return response
        except OCREngineError as exc:
            self._write_audit(
                action="ocr_extract_fields",
                decision="deny",
                reason="ocr_failed",
                target_id=source.source_media_id,
                trace_id=trace_id,
                meta={"error": str(exc), "payload": payload},
            )
            raise ValueError(f"OCR execution failed: {exc}") from exc

    def save_ocr_result(
        self,
        *,
        source_media_id: str,
        source_observation_id: str | None,
        ocr_mode: str,
        raw_text: str | None,
        fields_json: dict[str, Any],
        boxes_json: list[dict[str, Any]],
        language: str | None,
        confidence: float | None,
    ) -> OcrResult:
        result = OcrResult(
            id=f"ocr-{uuid4().hex[:12]}",
            source_media_id=require_non_empty(source_media_id, "source_media_id"),
            source_observation_id=source_observation_id,
            ocr_mode=require_non_empty(ocr_mode, "ocr_mode"),
            raw_text=raw_text,
            fields_json=json.dumps(fields_json, ensure_ascii=False, sort_keys=True),
            boxes_json=json.dumps(boxes_json, ensure_ascii=False, sort_keys=True),
            language=language,
            confidence=confidence,
            created_at=None,
        )
        return self._ocr_repo.save_ocr_result(result)

    def attach_ocr_result_to_observation(
        self,
        *,
        observation_id: str | None,
        raw_text: str | None,
    ) -> Observation | None:
        if not observation_id or not raw_text:
            return None
        return self._observation_repo.update_observation_ocr_text(observation_id, raw_text)

    def promote_ocr_to_event(
        self,
        *,
        payload: dict[str, Any],
        observation_id: str | None,
        raw_text: str | None,
        fields_json: dict[str, Any],
    ) -> Event | None:
        if not observation_id or not self.to_bool(payload.get("promote_to_event")):
            return None

        observation = self._observation_repo.get_observation(observation_id)
        if observation is None:
            raise ValueError(f"Observation not found: {observation_id}")

        event = Event(
            id=f"evt-{uuid4().hex[:12]}",
            observation_id=observation_id,
            event_type=self.as_optional_text(payload.get("event_type")) or "ocr_extracted",
            category="event",
            importance=self._normalize_importance(payload.get("importance")),
            camera_id=observation.camera_id,
            zone_id=observation.zone_id,
            object_name=observation.object_name,
            summary=self._build_event_summary(raw_text=raw_text, fields_json=fields_json),
            payload_json=json.dumps(
                {"raw_text": raw_text, "fields_json": fields_json},
                ensure_ascii=False,
                sort_keys=True,
            ),
            event_at=utc_now_iso8601(),
            created_at=None,
        )
        return self._event_repo.save_event(event)

    def _resolve_source(self, payload: dict[str, Any]) -> OCRSourceContext:
        media_id = self.as_optional_text(payload.get("media_id"))
        input_uri = self.as_optional_text(payload.get("input_uri")) or self.as_optional_text(
            payload.get("image_uri")
        )
        observation_id = self.as_optional_text(payload.get("observation_id")) or self.as_optional_text(
            payload.get("source_observation_id")
        )
        event_id = self.as_optional_text(payload.get("event_id"))

        event: Event | None = None
        if event_id:
            event = self._event_repo.get_event(event_id)
            if event is None:
                raise ValueError(f"event_id not found: {event_id}")

        if observation_id:
            if self._observation_repo.get_observation(observation_id) is None:
                raise ValueError(f"observation_id not found: {observation_id}")
        elif event and event.observation_id:
            observation_id = event.observation_id

        if media_id:
            media = self._media_repo.get_media_item(media_id)
            if media is None:
                raise ValueError(f"media_id not found: {media_id}")
            image_uri = input_uri or media.uri
            return OCRSourceContext(
                image_uri=require_non_empty(image_uri, "image_uri"),
                source_media_id=media.id,
                source_observation_id=observation_id,
                source_event_id=event_id,
            )

        image_uri = require_non_empty(input_uri, "input_uri or media_id")
        persisted_media = self._ensure_source_media(image_uri=image_uri, payload=payload)
        return OCRSourceContext(
            image_uri=image_uri,
            source_media_id=persisted_media.id,
            source_observation_id=observation_id,
            source_event_id=event_id,
        )

    def _ensure_source_media(self, *, image_uri: str, payload: dict[str, Any]) -> MediaItem:
        existing = self._media_repo.get_media_item_by_uri(image_uri)
        if existing is not None:
            return existing

        media_type = self.as_optional_text(payload.get("media_type")) or self._infer_media_type(image_uri)
        local_path = self._infer_local_path(image_uri)
        media = MediaItem(
            id=f"media-{uuid4().hex[:12]}",
            owner_type="ocr",
            owner_id="ocr-source",
            media_type=media_type,
            uri=image_uri,
            local_path=local_path,
            mime_type=self.as_optional_text(payload.get("mime_type")) or self._infer_mime_type(media_type),
            duration_sec=None,
            width=None,
            height=None,
            visibility_scope=self.as_optional_text(payload.get("visibility_scope")) or "private",
            sha256=None,
            created_at=None,
        )
        return self._media_repo.save_media_item(media)

    def _build_response(
        self,
        *,
        saved: OcrResult,
        fields_json: dict[str, Any],
        boxes_json: list[dict[str, Any]],
        source: OCRSourceContext,
        attached_observation: Observation | None,
        promoted_event: Event | None,
    ) -> dict[str, Any]:
        return {
            "ocr_result_id": saved.id,
            "ocr_mode": saved.ocr_mode,
            "raw_text": saved.raw_text,
            "fields_json": fields_json,
            "boxes_json": boxes_json,
            "language": saved.language,
            "confidence": saved.confidence,
            "source_media_id": source.source_media_id,
            "source_observation_id": source.source_observation_id,
            "source_event_id": source.source_event_id,
            "attached_observation_id": attached_observation.id if attached_observation else None,
            "promoted_event_id": promoted_event.id if promoted_event else None,
        }

    def _write_audit(
        self,
        *,
        action: str,
        decision: str,
        reason: str,
        target_id: str | None,
        trace_id: str | None,
        meta: dict[str, Any] | None,
    ) -> None:
        self._audit_repo.save_audit_log(
            AuditLog(
                id=f"audit-{uuid4().hex[:12]}",
                user_id=None,
                device_id=None,
                action=action,
                target_type="ocr",
                target_id=target_id,
                decision=decision,
                reason=reason,
                trace_id=trace_id,
                meta_json=json.dumps(meta, ensure_ascii=False, sort_keys=True, default=str) if meta else None,
                created_at=None,
            )
        )

    @staticmethod
    def _normalize_fields(raw_fields: Any) -> dict[str, Any]:
        if isinstance(raw_fields, dict):
            return {str(k): v for k, v in raw_fields.items()}
        return {}

    @staticmethod
    def _normalize_boxes(raw_boxes: Any) -> list[dict[str, Any]]:
        if isinstance(raw_boxes, list):
            normalized: list[dict[str, Any]] = []
            for item in raw_boxes:
                if isinstance(item, dict):
                    normalized.append({str(k): v for k, v in item.items()})
            return normalized
        return []

    @staticmethod
    def _normalize_importance(value: Any) -> int:
        try:
            parsed = int(value) if value is not None else 3
        except (TypeError, ValueError):
            parsed = 3
        return min(max(parsed, 1), 5)

    @staticmethod
    def _build_event_summary(*, raw_text: str | None, fields_json: dict[str, Any]) -> str:
        if raw_text and raw_text.strip():
            return raw_text[:200]
        if fields_json:
            kv = [f"{k}={v}" for k, v in fields_json.items()]
            return ", ".join(kv)[:200]
        return "ocr_extracted"

    @staticmethod
    def _infer_media_type(image_uri: str) -> str:
        suffix = Path(urlparse(image_uri).path).suffix.lower()
        if suffix in {".mp4", ".mov"}:
            return "video"
        if suffix in {".png", ".jpg", ".jpeg", ".bmp", ".webp"}:
            return "image"
        return "image"

    @staticmethod
    def _infer_mime_type(media_type: str) -> str:
        if media_type == "video":
            return "video/mp4"
        return "image/jpeg"

    @staticmethod
    def _infer_local_path(image_uri: str) -> str:
        parsed = urlparse(image_uri)
        if parsed.path and parsed.path.strip():
            return parsed.path
        safe_name = re.sub(r"[^a-zA-Z0-9._-]", "_", image_uri)[:64] or "ocr_source.jpg"
        return str(Path("./data/media/ocr") / safe_name)

    @staticmethod
    def as_optional_text(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text if text else None

    @staticmethod
    def to_float(value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def to_bool(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        if isinstance(value, (int, float)):
            return value != 0
        return False

    @staticmethod
    def to_key_list(values: Iterable[Any]) -> list[str]:
        return [str(item).strip() for item in values if str(item).strip()]
