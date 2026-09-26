import os
from dataclasses import dataclass
from pathlib import Path

from sftp_watcher.config.cyberark import CyberArkCCPConfig
from sftp_watcher.config.utils import (
    CredentialSource,
    bool_env,
    credential_source,
    csv_list,
    optional_path,
    required,
)


@dataclass(frozen=True)
class SFTPWatcherConfig:
    host: str
    port: int
    username: str
    password: str | None
    private_key_path: Path | None

    remote_dir: str
    local_dir: Path
    state_store_dir: Path

    poll_interval_seconds: int = 10
    max_depth: int = 1
    exclude_dirs: list[str] | None = None

    credential_source: CredentialSource = "config"
    cyberark_ccp: CyberArkCCPConfig | None = None

    cleanup_local_files_enabled: bool = True
    local_file_retention_days: int = 30
    cleanup_interval_seconds: int = 3600

    log_file: Path | None = None
    telemetry_enabled: bool = True
    telemetry_verify_tls: bool = True

    @classmethod
    def from_env(cls) -> "SFTPWatcherConfig":
        credential_source_value = credential_source(
            os.getenv("SFTP_CREDENTIAL_SOURCE", "config")
        )

        private_key = os.getenv("SFTP_PRIVATE_KEY_PATH")
        password = os.getenv("SFTP_PASSWORD")
        cyberark_ccp = None

        if credential_source_value == "config" and not password:
            raise ValueError(
                "Missing required environment variable: SFTP_PASSWORD "
                "when SFTP_CREDENTIAL_SOURCE=config"
            )

        if credential_source_value == "cyberark_ccp":
            cyberark_ccp = CyberArkCCPConfig.from_env(prefix="SFTP")

        return cls(
            host=required("SFTP_HOST"),
            port=int(os.getenv("SFTP_PORT", "22")),
            username=required("SFTP_USERNAME"),
            password=password,
            private_key_path=Path(private_key) if private_key else None,
            remote_dir=required("SFTP_REMOTE_DIR"),
            local_dir=Path(required("SFTP_LOCAL_DIR")),
            state_store_dir=Path(required("SFTP_STATE_STORE_DIR")),
            poll_interval_seconds=int(os.getenv("SFTP_POLL_INTERVAL_SECONDS", "10")),
            max_depth=int(os.getenv("SFTP_WALK_MAX_DEPTH", "1")),
            exclude_dirs=csv_list("SFTP_EXCLUDE_DIRS"),
            credential_source=credential_source_value,
            cyberark_ccp=cyberark_ccp,
            cleanup_local_files_enabled=bool_env(
                "CLEANUP_LOCAL_FILES_ENABLED", default=True
            ),
            local_file_retention_days=int(os.getenv("LOCAL_FILE_RETENTION_DAYS", "30")),
            cleanup_interval_seconds=int(os.getenv("CLEANUP_INTERVAL_SECONDS", "3600")),
            log_file=optional_path("SFTP_WATCHER_LOG_FILE"),
            telemetry_enabled=bool_env("SFTP_WATCHER_TELEMETRY_ENABLED", default=True),
            telemetry_verify_tls=bool_env(
                "SFTP_WATCHER_TELEMETRY_VERIFY_TLS",
                default=True,
            ),
        )
