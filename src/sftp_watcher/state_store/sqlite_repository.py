import sqlite3
from pathlib import Path

from sftp_watcher.state_store.models import (
    DownloadRecord,
    FileIdentity,
    ProcessState,
)


class SQLiteDownloadRecordRepository:
    def __init__(self, local_dir: Path) -> None:
        self._local_dir = local_dir
        self._db_path = self._local_dir / "download_state.sqlite3"

        self._local_dir.mkdir(parents=True, exist_ok=True)

        self._connection = sqlite3.connect(
            self._db_path,
            timeout=30,
        )
        self._connection.row_factory = sqlite3.Row

        result = self._connection.execute("PRAGMA journal_mode=WAL").fetchone()

        if result is None or str(result[0]).lower() != "wal":
            self._connection.close()
            raise RuntimeError("Could not enable SQLite WAL mode")

    def close(self) -> None:
        self._connection.close()

    def exists(self, identity: FileIdentity) -> bool:
        row = self._connection.execute(
            """
            SELECT 1
            FROM downloaded_files
            WHERE remote_path = ?
              AND size = ?
              AND mtime = ?
            LIMIT 1
            """,
            (
                identity.remote_path,
                identity.size,
                identity.mtime,
            ),
        ).fetchone()

        return row is not None

    def get(self, identity: FileIdentity) -> DownloadRecord | None:
        row = self._connection.execute(
            """
            SELECT name, remote_path, local_path, size, mtime, process_state
            FROM downloaded_files
            WHERE remote_path = ?
              AND size = ?
              AND mtime = ?
            """,
            (
                identity.remote_path,
                identity.size,
                identity.mtime,
            ),
        ).fetchone()

        if row is None:
            return None

        return self._record_from_row(row)

    def save(self, record: DownloadRecord) -> None:
        self._connection.execute(
            """
            INSERT INTO downloaded_files (
                name,
                remote_path,
                local_path,
                size,
                mtime,
                process_state
            )
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(remote_path, size, mtime)
            DO UPDATE SET
                name = excluded.name,
                local_path = excluded.local_path,
                process_state = excluded.process_state,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                record.name,
                record.remote_path,
                record.local_path,
                record.size,
                record.mtime,
                record.process_state,
            ),
        )
        self._connection.commit()

    def update_process_state(
        self,
        identity: FileIdentity,
        process_state: ProcessState,
    ) -> None:
        result = self._connection.execute(
            """
            UPDATE downloaded_files
            SET process_state = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE remote_path = ?
              AND size = ?
              AND mtime = ?
            """,
            (
                process_state,
                identity.remote_path,
                identity.size,
                identity.mtime,
            ),
        )
        self._connection.commit()

        if result.rowcount == 0:
            raise KeyError(f"Cannot update unknown file: {identity.remote_path}")

    def list_all(self) -> list[DownloadRecord]:
        rows = self._connection.execute(
            """
            SELECT name, remote_path, local_path, size, mtime, process_state
            FROM downloaded_files
            ORDER BY created_at ASC
            """
        ).fetchall()

        return [self._record_from_row(row) for row in rows]

    def list_by_process_state(
        self,
        process_state: ProcessState,
    ) -> list[DownloadRecord]:
        rows = self._connection.execute(
            """
            SELECT name, remote_path, local_path, size, mtime, process_state
            FROM downloaded_files
            WHERE process_state = ?
            ORDER BY created_at ASC
            """,
            (process_state,),
        ).fetchall()

        return [self._record_from_row(row) for row in rows]

    def _record_from_row(self, row: sqlite3.Row) -> DownloadRecord:
        return DownloadRecord(
            name=str(row["name"]),
            remote_path=str(row["remote_path"]),
            local_path=str(row["local_path"]),
            size=int(row["size"]),
            mtime=int(row["mtime"]),
            process_state=self._process_state_from_db(str(row["process_state"])),
        )

    def _process_state_from_db(self, value: str) -> ProcessState:
        if value == "pending":
            return "pending"

        if value == "success":
            return "success"

        if value == "failed":
            return "failed"

        raise ValueError(f"Invalid process_state from database: {value}")
