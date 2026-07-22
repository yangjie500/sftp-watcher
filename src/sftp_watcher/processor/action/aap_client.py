import logging
from typing import Any, Protocol

import requests
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from sftp_watcher.config import AAPConfig

tracer = trace.get_tracer(__name__)
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
        with tracer.start_as_current_span("aap.launch_job_template") as span:
            span.set_attribute("aap.job_template_id", self._config.job_template_id)
            span.set_attribute("http.request.method", "POST")

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

            span.set_attribute("http.response.status_code", response.status_code)

            try:
                response.raise_for_status()
            except requests.RequestException as error:
                span.record_exception(error)
                span.set_status(Status(StatusCode.ERROR))
                logger.exception(
                    "Failed to launch AAP job template: job_template_id=%s"
                    " status_code=%s",
                    self._config.job_template_id,
                    response.status_code,
                )
                raise

            payload = response.json()
            job_id = payload.get("job")

            if not isinstance(job_id, int):
                error = ValueError(
                    "AAP launch response did not contain a valid job id under key 'job'"
                )
                span.record_exception(error)
                span.set_status(Status(StatusCode.ERROR))
                raise error

            span.set_attribute("aap.job_id", job_id)

            logger.info(
                "AAP job template launched: job_template_id=%s job_id=%s",
                self._config.job_template_id,
                job_id,
            )

            return job_id

    def configure_password(self, password: str):
        self._password = password
