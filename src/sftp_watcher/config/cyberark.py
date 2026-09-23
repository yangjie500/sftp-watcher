import os
from dataclasses import dataclass
from pathlib import Path

from sftp_watcher.config.utils import bool_env, optional_path, required


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
            base_url=required(f"{env_prefix}_CYBERARK_CCP_BASE_URL"),
            app_id=required(f"{env_prefix}_CYBERARK_CCP_APP_ID"),
            safe=required(f"{env_prefix}_CYBERARK_CCP_SAFE"),
            object_name=required(f"{env_prefix}_CYBERARK_CCP_OBJECT_NAME"),
            timeout_seconds=float(
                os.getenv(f"{env_prefix}_CYBERARK_CCP_TIMEOUT_SECONDS", "10")
            ),
            verify_tls=bool_env(
                f"{env_prefix}_CYBERARK_CCP_VERIFY_TLS",
                default=True,
            ),
            ca_bundle_path=optional_path(f"{env_prefix}_CYBERARK_CCP_CA_BUNDLE_PATH"),
            folder=os.getenv(f"{env_prefix}_CYBERARK_CCP_FOLDER"),
            reason=os.getenv(f"{env_prefix}_CYBERARK_CCP_REASON"),
            client_cert_path=optional_path(
                f"{env_prefix}_CYBERARK_CCP_CLIENT_CERT_PATH"
            ),
            client_key_path=optional_path(f"{env_prefix}_CYBERARK_CCP_CLIENT_KEY_PATH"),
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
