from typing import Protocol

from sftp_watcher.state_store.models import (
    DownloadRecord,
    FileIdentity,
    ProcessState,
)


class DownloadRecordRepository(Protocol):
    def exists(self, identity: FileIdentity) -> bool: ...

    def get(self, identity: FileIdentity) -> DownloadRecord | None: ...

    def save(self, record: DownloadRecord) -> None: ...

    def update_process_state(
        self,
        identity: FileIdentity,
        process_state: ProcessState,
    ) -> None: ...

    def list_all(self) -> list[DownloadRecord]: ...

    def list_by_process_state(
        self,
        process_state: ProcessState,
    ) -> list[DownloadRecord]: ...
