from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import cast

import sftp_watcher.sftp_watcher as watcher_module
from sftp_watcher.config import SFTPWatcherConfig
from sftp_watcher.processor.processor import FileProcessorRouter
from sftp_watcher.sftp_client import RemoteEntry
from sftp_watcher.sftp_watcher import SFTPWatcher
from sftp_watcher.state_store.models import DownloadRecord, FileIdentity
from sftp_watcher.state_store.service import DownloadStateService


def test_sftp_watcher_uses_configured_filename_metadata_separator(
    tmp_path: Path,
) -> None:
    separators: list[str] = []

    def capture_separator(
        filename: str,
        *,
        metadata_names: Sequence[str],
        separator: str,
    ) -> dict[str, str]:
        separators.append(separator)
        return dict(zip(metadata_names, filename.split(separator), strict=False))

    sftp_client = FakeSFTPClient(
        entries=[
            RemoteEntry(
                name="tenant-a__my-project__1.2.3.tar.gz.bundle",
                path="upload/tenant-a__my-project__1.2.3.tar.gz.bundle",
                size=123,
                mtime=456,
            )
        ],
    )
    state_service = FakeDownloadStateService()

    original_extract_filename_metadata = watcher_module.extract_filename_metadata
    watcher_module.extract_filename_metadata = capture_separator

    try:
        watcher = SFTPWatcher(
            sftp_client=sftp_client,
            state_service=cast(DownloadStateService, state_service),
            processor_router=cast(FileProcessorRouter, FakeProcessorRouter()),
            config=_config(tmp_path),
            filename_metadata_separator="__",
        )

        watcher.poll_once()

        assert separators == ["__"]
        assert sftp_client.downloaded_remote_paths == [
            "upload/tenant-a__my-project__1.2.3.tar.gz.bundle",
        ]
        assert state_service.success_records == [
            "upload/tenant-a__my-project__1.2.3.tar.gz.bundle",
        ]
    finally:
        watcher_module.extract_filename_metadata = original_extract_filename_metadata


class FakeSFTPClient:
    def __init__(self, *, entries: list[RemoteEntry]) -> None:
        self._entries = entries
        self.downloaded_remote_paths: list[str] = []

    def connect(self) -> None:
        return None

    def list_files(self, remote_dir: str) -> list[RemoteEntry]:
        return self._entries

    def walk(
        self,
        remote_dir: str,
        *,
        exclude_dirs: list[str] | None = None,
        max_depth: int | None = None,
    ) -> Iterator[RemoteEntry]:
        yield from self._entries

    def download_file(self, remote_path: str, local_path: Path) -> None:
        self.downloaded_remote_paths.append(remote_path)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(b"bundle")

    def delete_file(self, remote_path: str) -> None:
        return None

    def read_bytes(self, remote_path: str, size: int, offset: int = 0) -> bytes:
        return b""

    def configure_username(self, username: str) -> None:
        return None

    def configure_password(self, password: str) -> None:
        return None

    def close(self) -> None:
        return None


class FakeDownloadStateService:
    def __init__(self) -> None:
        self.pending_records: list[DownloadRecord] = []
        self.success_records: list[str] = []

    def already_downloaded(self, record: DownloadRecord) -> bool:
        return False

    def mark_downloaded(self, record: DownloadRecord) -> None:
        self.pending_records.append(record)

    def list_pending(self) -> list[DownloadRecord]:
        return []

    def mark_success(self, identity: FileIdentity) -> None:
        self.success_records.append(identity.remote_path)

    def mark_failed(self, identity: FileIdentity) -> None:
        return None


class FakeProcessorRouter:
    def process(self, record: DownloadRecord) -> bool:
        return True


def _config(tmp_path: Path) -> SFTPWatcherConfig:
    return SFTPWatcherConfig(
        host="sftp.example.com",
        port=22,
        username="sftp-user",
        password="secret",
        private_key_path=None,
        remote_dir="upload",
        local_dir=tmp_path / "downloads",
        state_store_dir=tmp_path / "state",
    )
