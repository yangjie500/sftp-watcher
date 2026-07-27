import logging
from pathlib import Path
from typing import Any

from opentelemetry import trace
from opentelemetry.propagate import inject
from opentelemetry.trace import Span

from sftp_watcher.processor.action.aap_client import JobTemplateLauncher
from sftp_watcher.processor.tarball_metadata_extractor import (
    TarballMetadataExtractor,
)
from sftp_watcher.state_store.models import DownloadRecord

tracer = trace.get_tracer(__name__)
logger = logging.getLogger(__name__)


class TarballProcessor:
    GZIP_MAGIC = b"\x1f\x8b"
    TAR_MAGIC_OFFSET = 257
    TAR_MAGIC = b"ustar"

    def __init__(
        self,
        *,
        job_template_launcher: JobTemplateLauncher,
        metadata_extractor: TarballMetadataExtractor | None = None,
    ) -> None:
        self._job_template_launcher = job_template_launcher
        self._metadata_extractor = metadata_extractor or TarballMetadataExtractor()

    def can_process(self, record: DownloadRecord) -> bool:
        local_path = Path(record.local_path)

        if not local_path.exists() or not local_path.is_file():
            logger.debug(
                "Tarball processor skipped missing/non-file path: local_path=%s",
                local_path,
            )
            return False

        if self._looks_like_tar(local_path):
            logger.debug(
                "Tarball processor accepted file by tar magic: local_path=%s",
                local_path,
            )
            return True

        if self._looks_like_gzip(local_path):
            logger.debug(
                "Tarball processor accepted file by gzip magic: local_path=%s",
                local_path,
            )
            return True

        logger.debug(
            "Tarball processor skipped unsupported file: local_path=%s",
            local_path,
        )
        return False

    def process(self, record: DownloadRecord) -> None:
        with tracer.start_as_current_span("sftp_watcher.process_tarball") as span:
            span.set_attribute("sftp.remote_path", record.remote_path)
            span.set_attribute("sftp.local_path", record.local_path)
            span.set_attribute("sftp.file.size", record.size)
            span.set_attribute("sftp.file.mtime", record.mtime)

            local_path = Path(record.local_path)
            metadata: dict[str, Any] = {}

            try:
                metadata = self._metadata_extractor.extract(local_path)
            except Exception as error:
                span.record_exception(error)
                span.set_attribute("tarball.metadata.extracted", False)
                span.set_attribute("tarball.metadata.error", error.__class__.__name__)
                logger.warning(
                    "Failed to extract tarball metadata; continuing: "
                    "remote_path=%s local_path=%s",
                    record.remote_path,
                    local_path,
                    exc_info=True,
                )
            else:
                span.set_attribute("tarball.metadata.extracted", True)
                self._set_metadata_span_attributes(span, metadata)
                logger.info(
                    "Extracted tarball metadata: remote_path=%s local_path=%s "
                    "metadata=%s",
                    record.remote_path,
                    local_path,
                    metadata,
                )

            logger.info(
                "Processing tarball: remote_path=%s local_path=%s size=%s mtime=%s",
                record.remote_path,
                local_path,
                record.size,
                record.mtime,
            )

            logger.info(
                "Launching AAP job for tarball: remote_path=%s local_path=%s",
                record.remote_path,
                record.local_path,
            )

            carrier: dict[str, str] = {}
            inject(carrier)

            extra_vars = {
                "release_bundle_remote_path": record.remote_path,
            }

            traceparent = carrier.get("traceparent")
            if traceparent is not None:
                extra_vars["traceparent"] = traceparent

            tracestate = carrier.get("tracestate")
            if tracestate is not None:
                extra_vars["tracestate"] = tracestate

            job_id = self._job_template_launcher.launch_job_template(
                extra_vars=extra_vars,
            )

            span.set_attribute("aap.job_id", job_id)

            logger.info(
                "AAP job launched for tarball: remote_path=%s job_id=%s",
                record.remote_path,
                job_id,
            )

            logger.info(
                "Finished processing tarball: remote_path=%s local_path=%s",
                record.remote_path,
                local_path,
            )

    def _looks_like_gzip(self, path: Path) -> bool:
        with path.open("rb") as file:
            return file.read(2) == self.GZIP_MAGIC

    def _looks_like_tar(self, path: Path) -> bool:
        with path.open("rb") as file:
            file.seek(self.TAR_MAGIC_OFFSET)
            return file.read(len(self.TAR_MAGIC)) == self.TAR_MAGIC

    def _set_metadata_span_attributes(
        self,
        span: Span,
        metadata: dict[str, Any],
    ) -> None:
        span.set_attribute("tarball.metadata.size_of_file", metadata["SIZEOFFILE"])
        span.set_attribute("tarball.metadata.time_date", metadata["TIMEDATE"])
        span.set_attribute(
            "tarball.metadata.time_taken_seconds",
            metadata["TIME_TAKEN_SECONDS"],
        )
        span.set_attribute(
            "tarball.metadata.time_taken_minutes",
            metadata["TIME_TAKEN_MINUTES"],
        )
        span.set_attribute(
            "tarball.metadata.time_taken_hours",
            metadata["TIME_TAKEN_HOURS"],
        )
        span.set_attribute("tarball.metadata.size_kb", metadata["SIZE_KB"])
        span.set_attribute("tarball.metadata.size_mb", metadata["SIZE_MB"])
        span.set_attribute("tarball.metadata.size_gb", metadata["SIZE_GB"])
