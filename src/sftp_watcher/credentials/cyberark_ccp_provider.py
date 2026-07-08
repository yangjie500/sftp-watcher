import logging
from typing import Any

import requests

from sftp_watcher.config import CyberArkCCPConfig

logger = logging.getLogger(__name__)


class CyberArkCCPCredentialProvider:
    def __init__(
        self,
        config: CyberArkCCPConfig,
        *,
        credential_name: str = "credential",
    ) -> None:
        self._config = config
        self._credential_name = credential_name

    def get_credentials(self) -> str:
        logger.info(
            "Fetching %s from CyberArk CCP: "
            "base_url=%s app_id=%s safe=%s object_name=%s",
            self._credential_name,
            self._config.base_url,
            self._config.app_id,
            self._config.safe,
            self._config.object_name,
        )

        try:
            response = requests.get(
                self._account_url(),
                params=self._query_params(),
                timeout=self._config.timeout_seconds,
                verify=self._config.requests_verify_value(),
                cert=self._config.requests_client_cert_value(),
            )
            response.raise_for_status()

        except requests.RequestException:
            logger.exception(
                "Failed to fetch %s from CyberArk CCP: "
                "base_url=%s app_id=%s safe=%s object_name=%s",
                self._credential_name,
                self._config.base_url,
                self._config.app_id,
                self._config.safe,
                self._config.object_name,
            )
            raise

        try:
            payload = response.json()

        except ValueError:
            logger.exception(
                "CyberArk CCP response was not valid JSON while fetching %s: "
                "base_url=%s app_id=%s safe=%s object_name=%s",
                self._credential_name,
                self._config.base_url,
                self._config.app_id,
                self._config.safe,
                self._config.object_name,
            )
            raise

        credential = self._extract_credential(payload)

        logger.info(
            "Successfully fetched %s from CyberArk CCP: "
            "base_url=%s app_id=%s safe=%s object_name=%s",
            self._credential_name,
            self._config.base_url,
            self._config.app_id,
            self._config.safe,
            self._config.object_name,
        )

        return credential

    def _account_url(self) -> str:
        return f"{self._config.base_url.rstrip('/')}/AIMWebService/api/Accounts"

    def _query_params(self) -> dict[str, str]:
        params = {
            "AppID": self._config.app_id,
            "Safe": self._config.safe,
            "Object": self._config.object_name,
        }

        if self._config.folder is not None:
            params["Folder"] = self._config.folder

        if self._config.reason is not None:
            params["Reason"] = self._config.reason

        return params

    def _extract_credential(self, payload: dict[str, Any]) -> str:
        credential = payload.get("Content")

        if not isinstance(credential, str) or not credential:
            logger.error(
                "CyberArk CCP response did not contain valid Content for %s",
                self._credential_name,
            )
            raise ValueError(
                f"CyberArk CCP response did not contain valid Content for "
                f"{self._credential_name}"
            )

        return credential
