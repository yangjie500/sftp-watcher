from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from stat import S_ISDIR, S_ISREG
from typing import Protocol

import paramiko


@dataclass(frozen=True)
class RemoteEntry:
    name: str
    mtime: int
    size: int
    path: str


class SFTPClient(Protocol):
    def connect(self) -> None: ...

    def list_files(self, remote_dir: str) -> list[RemoteEntry]: ...

    def walk(
        self,
        remote_dir: str,
        *,
        exclude_dirs: list[str] | None = None,
        max_depth: int | None = None,
    ) -> Iterator[RemoteEntry]: ...

    def download_file(self, remote_path: str, local_path: Path) -> None: ...

    def delete_file(self, remote_path: str) -> None: ...

    def read_bytes(self, remote_path: str, size: int, offset: int = 0) -> bytes: ...

    def configure_username(self, username: str) -> None: ...

    def configure_password(self, password: str) -> None: ...

    def close(self) -> None: ...


class ParamikoSFTPClient:
    def __init__(
        self, host: str, port: int, username: str, password: str | None = None
    ):
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._ssh: paramiko.SSHClient | None = None
        self._sftp: paramiko.SFTPClient | None = None

    def connect(self):
        self._ssh = paramiko.SSHClient()
        self._ssh.load_system_host_keys()
        # self._ssh.set_missing_host_key_policy(paramiko.RejectPolicy())
        self._ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        self._ssh.connect(
            hostname=self._host,
            port=self._port,
            username=self._username,
            password=self._password,
        )

        self._sftp = self._ssh.open_sftp()

    def list_files(self, remote_dir: str) -> list[RemoteEntry]:
        if self._sftp is None:
            raise RuntimeError("SFTP client not connected")

        entries = self._sftp.listdir_attr(remote_dir)

        files: list[RemoteEntry] = []
        for entry in entries:
            if entry.st_mode is None or not S_ISREG(entry.st_mode):
                continue

            remote_path = str(PurePosixPath(remote_dir) / entry.filename)

            files.append(
                RemoteEntry(
                    name=entry.filename,
                    mtime=entry.st_mtime or 0,
                    size=entry.st_size or 0,
                    path=remote_path,
                )
            )

        return files

    def walk(
        self,
        remote_dir: str,
        *,
        exclude_dirs: list[str] | None = None,
        max_depth: int | None = None,
        _current_depth: int = 0,
    ) -> Iterator[RemoteEntry]:

        if self._sftp is None:
            raise RuntimeError("SFTP client not connected")

        _exclude_dirs = set(exclude_dirs or [])

        if max_depth is not None and _current_depth > max_depth:
            return

        for entry in self._sftp.listdir_attr(remote_dir):
            remote_path = str(PurePosixPath(remote_dir) / entry.filename)
            mode = entry.st_mode

            if mode is None:
                continue

            if S_ISDIR(mode):
                if entry.filename in _exclude_dirs:
                    continue

                yield from self.walk(
                    remote_path,
                    max_depth=max_depth,
                    exclude_dirs=exclude_dirs,
                    _current_depth=_current_depth + 1,
                )

            elif S_ISREG(mode):
                yield RemoteEntry(
                    path=remote_path,
                    name=entry.filename,
                    mtime=entry.st_mtime or 0,
                    size=entry.st_size or 0,
                )

    def download_file(self, remote_path: str, local_path: Path):
        if self._sftp is None:
            raise RuntimeError("SFTP client not connected")

        self._sftp.get(remote_path, str(local_path))

    def delete_file(self, remote_path: str) -> None:
        if self._sftp is None:
            raise RuntimeError("SFTP client not connected")

        self._sftp.remove(remote_path)

    def read_bytes(self, remote_path: str, size: int, offset: int = 0) -> bytes:
        if self._sftp is None:
            raise RuntimeError("SFTP client not connected")

        with self._sftp.open(remote_path, "rb") as file:
            file.seek(offset)
            data = file.read(size)

        if isinstance(data, str):
            return data.encode("utf-8")

        return data

    def configure_username(self, username: str) -> None:
        self._username = username

    def configure_password(self, password: str) -> None:
        self._password = password

    def close(self):
        if self._sftp:
            self._sftp.close()
        if self._ssh:
            self._ssh.close()
