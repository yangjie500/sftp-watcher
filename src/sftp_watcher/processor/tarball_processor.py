import logging
from pathlib import Path

from sftp_watcher.processor.action.aap_client import JobTemplateLauncher
from sftp_watcher.state_store.models import DownloadRecord

logger = logging.getLogger(__name__)


class TarballProcessor:
    GZIP_MAGIC = b"\x1f\x8b"
    TAR_MAGIC_OFFSET = 257
    TAR_MAGIC = b"ustar"

    def __init__(
        self,
        *,
        job_template_launcher: JobTemplateLauncher,
    ) -> None:
        self._job_template_launcher = job_template_launcher

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
        local_path = Path(record.local_path)

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

        job_id = self._job_template_launcher.launch_job_template(
            extra_vars={
                "release_bundle_remote_path": record.remote_path,
            }
        )

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
