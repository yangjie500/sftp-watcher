from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from sftp_watcher.sftp_client import RemoteEntry

ProcessState = Literal["pending", "success", "failed"]


@dataclass(frozen=True)
class FileIdentity:
    remote_path: str
    size: int
    mtime: int


@dataclass(frozen=True)
class DownloadRecord:
    name: str
    remote_path: str
    local_path: str
    size: int
    mtime: int
    process_state: ProcessState = "pending"

    @property
    def identity(self) -> FileIdentity:
        return FileIdentity(
            remote_path=self.remote_path,
            size=self.size,
            mtime=self.mtime,
        )

    @classmethod
    def from_remote_entry(
        cls,
        entry: RemoteEntry,
        *,
        local_path: Path,
        process_state: ProcessState = "pending",
    ) -> "DownloadRecord":
        return cls(
            name=entry.name,
            remote_path=entry.path,
            local_path=str(local_path),
            size=entry.size,
            mtime=entry.mtime,
            process_state=process_state,
        )

    def with_process_state(self, process_state: ProcessState) -> "DownloadRecord":
        return DownloadRecord(
            name=self.name,
            remote_path=self.remote_path,
            local_path=self.local_path,
            size=self.size,
            mtime=self.mtime,
            process_state=process_state,
        )
