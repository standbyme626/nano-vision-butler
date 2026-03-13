"""Runtime wiring for MCP tools/resources/prompts."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Generator

from src.db.repositories.audit_repo import AuditRepo
from src.db.repositories.device_repo import DeviceRepo
from src.db.repositories.event_repo import EventRepo
from src.db.repositories.media_repo import MediaRepo
from src.db.repositories.observation_repo import ObservationRepo
from src.db.repositories.ocr_repo import OcrRepo
from src.db.repositories.state_repo import StateRepo
from src.db.session import SQLiteSessionFactory, initialize_database
from src.security.security_guard import SecurityGuard
from src.services.device_service import DeviceService
from src.services.ocr_service import OCRService
from src.services.policy_service import PolicyService
from src.services.state_service import StateService
from src.settings import AppConfig, load_settings


@dataclass(frozen=True)
class ServiceBundle:
    device_repo: DeviceRepo
    observation_repo: ObservationRepo
    event_repo: EventRepo
    state_repo: StateRepo
    audit_repo: AuditRepo
    media_repo: MediaRepo
    ocr_repo: OcrRepo
    security_guard: SecurityGuard
    device_service: DeviceService
    state_service: StateService
    policy_service: PolicyService
    ocr_service: OCRService


class MCPRuntime:
    """Owns config and database session lifecycle for MCP invocations."""

    def __init__(
        self,
        *,
        config_dir: str | Path | None = None,
        repo_root: str | Path | None = None,
    ) -> None:
        self.repo_root = Path(repo_root) if repo_root else Path(__file__).resolve().parents[2]
        self.config_dir = Path(config_dir) if config_dir else (self.repo_root / "config")
        self.config: AppConfig = load_settings(self.config_dir)

        db_path = self._resolve_db_path()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        initialize_database(db_path=db_path, schema_path=self.repo_root / "schema.sql")
        self.session_factory = SQLiteSessionFactory(db_path)

    def _resolve_db_path(self) -> Path:
        configured = Path(self.config.settings["database"]["path"])
        if configured.is_absolute():
            return configured
        return self.repo_root / configured

    @contextmanager
    def services(self) -> Generator[ServiceBundle, None, None]:
        with self.session_factory.connect() as conn:
            device_repo = DeviceRepo(conn)
            observation_repo = ObservationRepo(conn)
            event_repo = EventRepo(conn)
            state_repo = StateRepo(conn)
            audit_repo = AuditRepo(conn)
            media_repo = MediaRepo(conn)
            ocr_repo = OcrRepo(conn)
            security_guard = SecurityGuard(
                config=self.config,
                audit_repo=audit_repo,
                device_repo=device_repo,
                media_repo=media_repo,
            )

            state_service = StateService(
                state_repo=state_repo,
                observation_repo=observation_repo,
                conn=conn,
                config=self.config,
            )
            policy_service = PolicyService(
                state_service=state_service,
                device_repo=device_repo,
                config=self.config,
            )
            device_service = DeviceService(
                device_repo=device_repo,
                media_repo=media_repo,
                audit_repo=audit_repo,
                config=self.config,
            )
            ocr_service = OCRService(
                media_repo=media_repo,
                observation_repo=observation_repo,
                event_repo=event_repo,
                ocr_repo=ocr_repo,
                audit_repo=audit_repo,
            )
            yield ServiceBundle(
                device_repo=device_repo,
                observation_repo=observation_repo,
                event_repo=event_repo,
                state_repo=state_repo,
                audit_repo=audit_repo,
                media_repo=media_repo,
                ocr_repo=ocr_repo,
                security_guard=security_guard,
                device_service=device_service,
                state_service=state_service,
                policy_service=policy_service,
                ocr_service=ocr_service,
            )
