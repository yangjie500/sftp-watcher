import os
from dataclasses import dataclass
from pathlib import Path

from sftp_watcher.config.cyberark import CyberArkCCPConfig
from sftp_watcher.config.utils import (
    AAPAuthMethod,
    CredentialSource,
    aap_auth_method,
    bool_env,
    credential_source,
    optional_path,
    required,
)


@dataclass(frozen=True)
class AAPConfig:
    base_url: str
    token: str | None
    job_template_id: int

    password: str | None = None
    auth_method: AAPAuthMethod = "token"
    username: str | None = None

    timeout_seconds: float = 30.0
    verify_tls: bool = True
    ca_bundle_path: Path | None = None

    credential_source: CredentialSource = "config"
    cyberark_ccp: CyberArkCCPConfig | None = None

    @classmethod
    def from_env(cls) -> "AAPConfig":
        credential_source_value = credential_source(
            os.getenv("AAP_CREDENTIAL_SOURCE", "config")
        )
        auth_method = aap_auth_method(os.getenv("AAP_AUTH_METHOD", "token"))

        token = os.getenv("AAP_TOKEN")
        username = os.getenv("AAP_USERNAME")
        password = os.getenv("AAP_PASSWORD")
        cyberark_ccp = None

        if credential_source_value == "config" and auth_method == "token" and not token:
            raise ValueError(
                "Missing required environment variable: AAP_TOKEN "
                "when AAP_CREDENTIAL_SOURCE=config and AAP_AUTH_METHOD=token"
            )

        if auth_method == "basic" and not username:
            raise ValueError(
                "Missing required environment variable: AAP_USERNAME "
                "when AAP_AUTH_METHOD=basic"
            )

        if (
            credential_source_value == "config"
            and auth_method == "basic"
            and not password
        ):
            raise ValueError(
                "Missing required environment variable: AAP_PASSWORD "
                "when AAP_CREDENTIAL_SOURCE=config and AAP_AUTH_METHOD=basic"
            )

        if credential_source_value == "cyberark_ccp":
            cyberark_ccp = CyberArkCCPConfig.from_env(prefix="AAP")

        return cls(
            base_url=required("AAP_BASE_URL"),
            token=token,
            job_template_id=int(required("AAP_JOB_TEMPLATE_ID")),
            password=password,
            auth_method=auth_method,
            username=username,
            timeout_seconds=float(os.getenv("AAP_TIMEOUT_SECONDS", "30")),
            verify_tls=bool_env("AAP_VERIFY_TLS", default=True),
            ca_bundle_path=optional_path("AAP_CA_BUNDLE_PATH"),
            credential_source=credential_source_value,
            cyberark_ccp=cyberark_ccp,
        )

    def requests_verify_value(self) -> bool | str:
        if not self.verify_tls:
            return False

        if self.ca_bundle_path is not None:
            return str(self.ca_bundle_path)

        return True
