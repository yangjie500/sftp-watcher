import logging
import time
from pathlib import Path

from sftp_watcher.lifecycles.lifecycle import PollLifecycleContext

logger = logging.getLogger(__name__)


def cleanup_old_local_files(
    *,
    local_dir: Path,
    retention_days: int,
) -> None:
    cutoff_time = time.time() - (retention_days * 24 * 60 * 60)

    logger.info(
        "Starting local file cleanup: local_dir=%s retention_days=%s",
        local_dir,
        retention_days,
    )

    deleted_count = 0

    for path in local_dir.rglob("*"):
        if not path.is_file():
            continue

        if path.name.endswith(".tmp"):
            continue

        if path.stat().st_mtime >= cutoff_time:
            continue

        try:
            path.unlink()
            deleted_count += 1

            logger.info(
                "Deleted old local file: path=%s",
                path,
            )

        except Exception:
            logger.exception(
                "Failed to delete old local file: path=%s",
                path,
            )

    logger.info(
        "Completed local file cleanup: local_dir=%s deleted_count=%s",
        local_dir,
        deleted_count,
    )


class LocalFileCleanupLifecycle:
    def __init__(
        self,
        *,
        local_dir: Path,
        retention_days: int,
        cleanup_interval_seconds: int = 3600,
        enabled: bool = True,
    ) -> None:
        self._local_dir = local_dir
        self._retention_days = retention_days
        self._cleanup_interval_seconds = cleanup_interval_seconds
        self._enabled = enabled
        self._last_cleanup_time: float | None = None

    def before_poll(self, context: PollLifecycleContext) -> None:
        pass

    def after_poll(self, context: PollLifecycleContext) -> None:
        if not self._enabled:
            return

        now = time.time()

        if (
            self._last_cleanup_time is not None
            and now - self._last_cleanup_time < self._cleanup_interval_seconds
        ):
            return

        self._last_cleanup_time = now

        cleanup_old_local_files(
            local_dir=self._local_dir,
            retention_days=self._retention_days,
        )
