import logging
from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from sftp_watcher.state_store.models import DownloadRecord

logger = logging.getLogger(__name__)


class FileProcessor(Protocol):
    def can_process(self, record: DownloadRecord) -> bool: ...

    def process(
        self,
        record: DownloadRecord,
    ) -> None: ...


@runtime_checkable
class PeriodicProcessor(Protocol):
    def on_poll_complete(self) -> None: ...


class FileProcessorRouter:
    """
    Routes downloaded files to the first processor that can handle them.

    Processor order matters. More specific processors should be registered
    before generic or fallback processors.
    """

    def __init__(self, processors: Sequence[FileProcessor]) -> None:
        self._processors = tuple(processors)

    def process(self, record: DownloadRecord) -> bool:
        """
        Process a downloaded file using the first matching processor.

        Returns:
            True if a processor handled the file.
            False if no processor could handle the file.
        """
        processor = self._find_processor(record)

        if processor is None:
            logger.warning(
                "No processor found for file: remote_path=%s local_path=%s",
                record.remote_path,
                record.local_path,
            )
            return False

        logger.info(
            "Processing file: remote_path=%s local_path=%s processor=%s",
            record.remote_path,
            record.local_path,
            processor.__class__.__name__,
        )

        processor.process(record)

        logger.info(
            "Processed file successfully: remote_path=%s local_path=%s processor=%s",
            record.remote_path,
            record.local_path,
            processor.__class__.__name__,
        )

        return True

    def on_poll_complete(self) -> None:
        """
        Notify processors that one watcher polling cycle has completed.

        Only processors that implement PeriodicProcessor will receive this hook.
        """
        for processor in self._processors:
            if not isinstance(processor, PeriodicProcessor):
                continue

            logger.debug(
                "Running on_poll_complete for processor=%s",
                processor.__class__.__name__,
            )

            processor.on_poll_complete()

    def _find_processor(self, record: DownloadRecord) -> FileProcessor | None:
        for processor in self._processors:
            if processor.can_process(record):
                return processor

        return None
