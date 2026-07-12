import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv

CredentialSource = Literal["config", "cyberark_ccp"]


@dataclass(frozen=True)
class CyberArkCCPConfig:
    base_url: str
    app_id: str
    safe: str
    object_name: str

    timeout_seconds: float = 10.0
    verify_tls: bool = True
    ca_bundle_path: Path | None = None

    folder: str | None = None
    reason: str | None = None

    client_cert_path: Path | None = None
    client_key_path: Path | None = None

    @classmethod
    def from_env(cls, *, prefix: str) -> "CyberArkCCPConfig":
        env_prefix = prefix.upper()

        return cls(
            base_url=_required(f"{env_prefix}_CYBERARK_CCP_BASE_URL"),
            app_id=_required(f"{env_prefix}_CYBERARK_CCP_APP_ID"),
            safe=_required(f"{env_prefix}_CYBERARK_CCP_SAFE"),
            object_name=_required(f"{env_prefix}_CYBERARK_CCP_OBJECT_NAME"),
            timeout_seconds=float(
                os.getenv(f"{env_prefix}_CYBERARK_CCP_TIMEOUT_SECONDS", "10")
            ),
            verify_tls=_bool(
                f"{env_prefix}_CYBERARK_CCP_VERIFY_TLS",
                default=True,
            ),
            ca_bundle_path=_optional_path(f"{env_prefix}_CYBERARK_CCP_CA_BUNDLE_PATH"),
            folder=os.getenv(f"{env_prefix}_CYBERARK_CCP_FOLDER"),
            reason=os.getenv(f"{env_prefix}_CYBERARK_CCP_REASON"),
            client_cert_path=_optional_path(
                f"{env_prefix}_CYBERARK_CCP_CLIENT_CERT_PATH"
            ),
            client_key_path=_optional_path(
                f"{env_prefix}_CYBERARK_CCP_CLIENT_KEY_PATH"
            ),
        )

    def requests_verify_value(self) -> bool | str:
        if not self.verify_tls:
            return False

        if self.ca_bundle_path is not None:
            return str(self.ca_bundle_path)

        return True

    def requests_client_cert_value(self) -> str | tuple[str, str] | None:
        if self.client_cert_path is None:
            return None

        if self.client_key_path is None:
            return str(self.client_cert_path)

        return (
            str(self.client_cert_path),
            str(self.client_key_path),
        )


@dataclass(frozen=True)
class AAPConfig:
    base_url: str
    token: str | None
    job_template_id: int

    timeout_seconds: float = 30.0
    verify_tls: bool = True
    ca_bundle_path: Path | None = None

    credential_source: CredentialSource = "config"
    cyberark_ccp: CyberArkCCPConfig | None = None

    @classmethod
    def from_env(cls, env_file: Path | None = None) -> "AAPConfig":
        if env_file:
            load_dotenv(env_file)
        else:
            load_dotenv()

        credential_source = _credential_source(
            os.getenv("AAP_CREDENTIAL_SOURCE", "config")
        )

        token = os.getenv("AAP_TOKEN")
        cyberark_ccp = None

        if credential_source == "config" and not token:
            raise ValueError(
                "Missing required environment variable: AAP_TOKEN "
                "when AAP_CREDENTIAL_SOURCE=config"
            )

        if credential_source == "cyberark_ccp":
            cyberark_ccp = CyberArkCCPConfig.from_env(prefix="AAP")

        return cls(
            base_url=_required("AAP_BASE_URL"),
            token=token,
            job_template_id=int(_required("AAP_JOB_TEMPLATE_ID")),
            timeout_seconds=float(os.getenv("AAP_TIMEOUT_SECONDS", "30")),
            verify_tls=_bool("AAP_VERIFY_TLS", default=True),
            ca_bundle_path=_optional_path("AAP_CA_BUNDLE_PATH"),
            credential_source=credential_source,
            cyberark_ccp=cyberark_ccp,
        )

    def requests_verify_value(self) -> bool | str:
        if not self.verify_tls:
            return False

        if self.ca_bundle_path is not None:
            return str(self.ca_bundle_path)

        return True


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

    @classmethod
    def from_env(cls, env_file: Path | None = None) -> "SFTPWatcherConfig":
        if env_file:
            load_dotenv(env_file)
        else:
            load_dotenv()

        credential_source = _credential_source(
            os.getenv("SFTP_CREDENTIAL_SOURCE", "config")
        )

        private_key = os.getenv("SFTP_PRIVATE_KEY_PATH")
        password = os.getenv("SFTP_PASSWORD")
        cyberark_ccp = None

        if credential_source == "config" and not password:
            raise ValueError(
                "Missing required environment variable: SFTP_PASSWORD "
                "when SFTP_CREDENTIAL_SOURCE=config"
            )

        if credential_source == "cyberark_ccp":
            cyberark_ccp = CyberArkCCPConfig.from_env(prefix="SFTP")

        return cls(
            host=_required("SFTP_HOST"),
            port=int(os.getenv("SFTP_PORT", "22")),
            username=_required("SFTP_USERNAME"),
            password=password,
            private_key_path=Path(private_key) if private_key else None,
            remote_dir=_required("SFTP_REMOTE_DIR"),
            local_dir=Path(_required("SFTP_LOCAL_DIR")),
            state_store_dir=Path(_required("SFTP_STATE_STORE_DIR")),
            poll_interval_seconds=int(os.getenv("SFTP_POLL_INTERVAL_SECONDS", "10")),
            max_depth=int(os.getenv("SFTP_WALK_MAX_DEPTH", "1")),
            exclude_dirs=_csv_list("SFTP_EXCLUDE_DIRS"),
            credential_source=credential_source,
            cyberark_ccp=cyberark_ccp,
            cleanup_local_files_enabled=_bool(
                "CLEANUP_LOCAL_FILES_ENABLED", default=True
            ),
            local_file_retention_days=int(os.getenv("LOCAL_FILE_RETENTION_DAYS", "30")),
            cleanup_interval_seconds=int(os.getenv("CLEANUP_INTERVAL_SECONDS", "3600")),
        )


def _required(name: str) -> str:
    value = os.getenv(name)

    if not value:
        raise ValueError(f"Missing required environment variable: {name}")

    return value


def _csv_list(name: str) -> list[str] | None:
    value = os.getenv(name)

    if value is None or value.strip() == "":
        return None

    return [item.strip() for item in value.split(",") if item.strip()]


def _credential_source(value: str) -> CredentialSource:
    if value == "config":
        return "config"

    if value == "cyberark_ccp":
        return "cyberark_ccp"

    raise ValueError(
        "Invalid XXX_CREDENTIAL_SOURCE. Expected one of: config, cyberark_ccp"
    )


def _bool(name: str, *, default: bool) -> bool:
    value = os.getenv(name)

    if value is None or value.strip() == "":
        return default

    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _optional_path(name: str) -> Path | None:
    value = os.getenv(name)

    if value is None or value.strip() == "":
        return None

    return Path(value)
