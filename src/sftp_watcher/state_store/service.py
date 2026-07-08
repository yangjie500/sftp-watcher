from sftp_watcher.state_store.models import (
    DownloadRecord,
    FileIdentity,
)
from sftp_watcher.state_store.repository import DownloadRecordRepository


class DownloadStateService:
    def __init__(self, repository: DownloadRecordRepository) -> None:
        self._repository = repository

    def already_downloaded(self, record: DownloadRecord) -> bool:
        return self._repository.exists(record.identity)

    def mark_downloaded(self, record: DownloadRecord) -> None:
        if self._repository.exists(record.identity):
            return

        self._repository.save(record.with_process_state("pending"))

    def get(self, identity: FileIdentity) -> DownloadRecord | None:
        return self._repository.get(identity)

    def mark_pending(self, identity: FileIdentity) -> None:
        self._repository.update_process_state(identity, "pending")

    def mark_success(self, identity: FileIdentity) -> None:
        self._repository.update_process_state(identity, "success")

    def mark_failed(self, identity: FileIdentity) -> None:
        self._repository.update_process_state(identity, "failed")

    def list_pending(self) -> list[DownloadRecord]:
        return self._repository.list_by_process_state("pending")

    def list_success(self) -> list[DownloadRecord]:
        return self._repository.list_by_process_state("success")

    def list_failed(self) -> list[DownloadRecord]:
        return self._repository.list_by_process_state("failed")

    def list_all(self) -> list[DownloadRecord]:
        return self._repository.list_all()
