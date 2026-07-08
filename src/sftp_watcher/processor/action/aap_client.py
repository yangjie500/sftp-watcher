import logging
from typing import Any, Protocol

import requests

from sftp_watcher.config import AAPConfig

logger = logging.getLogger(__name__)


class JobTemplateLauncher(Protocol):
    def launch_job_template(
        self,
        *,
        extra_vars: dict[str, Any],
    ) -> int: ...


class AAPClient:
    def __init__(self, config: AAPConfig) -> None:
        self._config = config
        self._password = config.token

    def launch_job_template(
        self,
        *,
        extra_vars: dict[str, Any],
    ) -> int:
        url = (
            f"{self._config.base_url.rstrip('/')}"
            f"/api/v2/job_templates/{self._config.job_template_id}/launch/"
        )

        logger.info(
            "Launching AAP job template: job_template_id=%s extra_var_keys=%s",
            self._config.job_template_id,
            sorted(extra_vars.keys()),
        )

        response = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {self._password}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            json={
                "extra_vars": extra_vars,
            },
            timeout=self._config.timeout_seconds,
            verify=self._config.requests_verify_value(),
        )

        try:
            response.raise_for_status()
        except requests.RequestException:
            logger.exception(
                "Failed to launch AAP job template: job_template_id=%s status_code=%s",
                self._config.job_template_id,
                response.status_code,
            )
            raise

        payload = response.json()
        job_id = payload.get("job")

        if not isinstance(job_id, int):
            raise ValueError(
                "AAP launch response did not contain a valid job id under key 'job'"
            )

        logger.info(
            "AAP job template launched: job_template_id=%s job_id=%s",
            self._config.job_template_id,
            job_id,
        )

        return job_id

    def configure_password(self, password: str):
        self._password = password
