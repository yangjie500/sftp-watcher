import logging
import shutil
from collections.abc import Sequence
from pathlib import Path, PurePosixPath

from sftp_watcher.config import SFTPWatcherConfig
from sftp_watcher.lifecycles.lifecycle import PollLifecycle, PollLifecycleContext
from sftp_watcher.processor.processor import FileProcessorRouter
from sftp_watcher.sftp_client import RemoteEntry, SFTPClient
from sftp_watcher.state_store.models import DownloadRecord
from sftp_watcher.state_store.service import DownloadStateService

logger = logging.getLogger(__name__)


class SFTPWatcher:
    def __init__(
        self,
        *,
        sftp_client: SFTPClient,
        state_service: DownloadStateService,
        processor_router: FileProcessorRouter,
        config: SFTPWatcherConfig,
        lifecycles: Sequence[PollLifecycle] = (),
    ) -> None:
        self._sftp_client = sftp_client
        self._state_service = state_service
        self._processor_router = processor_router
        self._config = config
        self._lifecycles = tuple(lifecycles)

    def poll_once(self) -> None:
        """
        Run one watcher cycle.

        1. Discover files from SFTP.
        2. Download new files.
        3. Save downloaded records as pending.
        4. Process pending records.
        5. Mark success or failed.
        """
        context = PollLifecycleContext(
            remote_dir=self._config.remote_dir,
            local_dir=Path(self._config.local_dir),
        )

        logger.info("Starting SFTP watcher poll")

        self._before_poll(context)
        self._sftp_client.connect()

        try:
            self._download_new_files()
            self._process_pending_records()
        finally:
            self._sftp_client.close()
            self._after_poll(context)

        logger.info("Completed SFTP watcher poll")

    def _before_poll(self, context: PollLifecycleContext) -> None:
        for lifecycle in self._lifecycles:
            logger.debug(
                "Running before_poll lifecycle: lifecycle=%s",
                lifecycle.__class__.__name__,
            )
            lifecycle.before_poll(context)

    def _after_poll(self, context: PollLifecycleContext) -> None:
        for lifecycle in reversed(self._lifecycles):
            try:
                logger.debug(
                    "Running after_poll lifecycle: lifecycle=%s",
                    lifecycle.__class__.__name__,
                )
                lifecycle.after_poll(context)
            except Exception:
                logger.exception(
                    "after_poll lifecycle failed: lifecycle=%s",
                    lifecycle.__class__.__name__,
                )

    def _download_new_files(self) -> None:
        remote_entries = self._list_remote_entries()

        for remote_entry in remote_entries:
            local_path = self._local_path_for(remote_entry)

            record = DownloadRecord.from_remote_entry(
                remote_entry,
                local_path=local_path,
                process_state="pending",
            )

            if self._state_service.already_downloaded(record):
                logger.debug(
                    "Skipping already downloaded file: remote_path=%s",
                    record.remote_path,
                )
                continue

            logger.info(
                "Downloading new file: remote_path=%s local_path=%s",
                record.remote_path,
                record.local_path,
            )

            self._download_remote_entry(remote_entry, local_path)

            self._state_service.mark_downloaded(record)

            logger.info(
                "Marked file as downloaded: remote_path=%s local_path=%s",
                record.remote_path,
                record.local_path,
            )

    def _process_pending_records(self) -> None:
        pending_records = self._state_service.list_pending()

        logger.info("Found %d pending record(s)", len(pending_records))

        for record in pending_records:
            logger.info(
                "Processing pending record: remote_path=%s local_path=%s",
                record.remote_path,
                record.local_path,
            )

            try:
                handled = self._processor_router.process(record)

                if handled:
                    self._state_service.mark_success(record.identity)
                    logger.info(
                        "Marked record as success: remote_path=%s",
                        record.remote_path,
                    )
                else:
                    self._state_service.mark_failed(record.identity)
                    logger.warning(
                        "Marked record as failed because no processor handled it: "
                        "remote_path=%s",
                        record.remote_path,
                    )

            except Exception:
                self._state_service.mark_failed(record.identity)

                logger.exception(
                    "Marked record as failed after processor error: remote_path=%s",
                    record.remote_path,
                )

    def _list_remote_entries(self) -> list[RemoteEntry]:
        entries = self._sftp_client.walk(
            self._config.remote_dir,
            max_depth=self._config.max_depth,
            exclude_dirs=self._config.exclude_dirs,
        )

        return list(entries)

    def _download_remote_entry(
        self,
        remote_entry: RemoteEntry,
        local_path: Path,
    ) -> None:
        local_path.parent.mkdir(parents=True, exist_ok=True)

        temp_path = local_path.with_name(f"{local_path.name}.tmp")

        try:
            self._sftp_client.download_file(
                remote_path=remote_entry.path,
                local_path=temp_path,
            )

            shutil.move(str(temp_path), str(local_path))

        finally:
            if temp_path.exists():
                temp_path.unlink()

    def _local_path_for(self, remote_entry: RemoteEntry) -> Path:
        relative_path = self._relative_remote_path(remote_entry.path)

        return self._config.local_dir / relative_path

    def _relative_remote_path(self, remote_path: str) -> Path:
        remote_root = PurePosixPath(self._config.remote_dir)
        remote_file_path = PurePosixPath(remote_path)

        try:
            relative_posix_path = remote_file_path.relative_to(remote_root)
        except ValueError:
            relative_posix_path = PurePosixPath(remote_file_path.name)

        safe_parts = [
            part for part in relative_posix_path.parts if part not in {"", ".", ".."}
        ]

        return Path(*safe_parts)
