from pathlib import Path

import pytest

from sftp_watcher.state_store.models import DownloadRecord, FileIdentity
from sftp_watcher.state_store.sqlite_repository import SQLiteDownloadRecordRepository


def test_sqlite_repository_creates_database_file(tmp_path: Path) -> None:
    repository = SQLiteDownloadRecordRepository(tmp_path)

    repository.close()

    assert (tmp_path / "download_state.sqlite3").exists()


def test_sqlite_repository_exists_returns_false_when_record_does_not_exist(
    tmp_path: Path,
) -> None:
    repository = SQLiteDownloadRecordRepository(tmp_path)

    identity = FileIdentity(
        remote_path="/remote/incoming/report.csv",
        size=123,
        mtime=1719230000,
    )

    assert repository.exists(identity) is False

    repository.close()


def test_sqlite_repository_save_and_get_record(tmp_path: Path) -> None:
    repository = SQLiteDownloadRecordRepository(tmp_path)

    record = DownloadRecord(
        name="report.csv",
        remote_path="/remote/incoming/report.csv",
        local_path="/data/downloads/report.csv",
        size=123,
        mtime=1719230000,
        process_state="pending",
    )

    repository.save(record)

    saved_record = repository.get(record.identity)

    assert saved_record == record

    repository.close()


def test_sqlite_repository_exists_returns_true_after_save(tmp_path: Path) -> None:
    repository = SQLiteDownloadRecordRepository(tmp_path)

    record = DownloadRecord(
        name="report.csv",
        remote_path="/remote/incoming/report.csv",
        local_path="/data/downloads/report.csv",
        size=123,
        mtime=1719230000,
    )

    repository.save(record)

    assert repository.exists(record.identity) is True

    repository.close()


def test_sqlite_repository_save_upserts_existing_record(tmp_path: Path) -> None:
    repository = SQLiteDownloadRecordRepository(tmp_path)

    original_record = DownloadRecord(
        name="report.csv",
        remote_path="/remote/incoming/report.csv",
        local_path="/data/downloads/report.csv",
        size=123,
        mtime=1719230000,
        process_state="pending",
    )

    updated_record = DownloadRecord(
        name="report.csv",
        remote_path="/remote/incoming/report.csv",
        local_path="/data/downloads/report-v2.csv",
        size=123,
        mtime=1719230000,
        process_state="success",
    )

    repository.save(original_record)
    repository.save(updated_record)

    saved_record = repository.get(original_record.identity)

    assert saved_record == updated_record
    assert len(repository.list_all()) == 1

    repository.close()


def test_sqlite_repository_update_process_state(tmp_path: Path) -> None:
    repository = SQLiteDownloadRecordRepository(tmp_path)

    record = DownloadRecord(
        name="report.csv",
        remote_path="/remote/incoming/report.csv",
        local_path="/data/downloads/report.csv",
        size=123,
        mtime=1719230000,
        process_state="pending",
    )

    repository.save(record)
    repository.update_process_state(record.identity, "success")

    saved_record = repository.get(record.identity)

    assert saved_record is not None
    assert saved_record.process_state == "success"

    repository.close()


def test_sqlite_repository_update_process_state_raises_for_unknown_file(
    tmp_path: Path,
) -> None:
    repository = SQLiteDownloadRecordRepository(tmp_path)

    identity = FileIdentity(
        remote_path="/remote/incoming/missing.csv",
        size=123,
        mtime=1719230000,
    )

    with pytest.raises(KeyError, match="Cannot update unknown file"):
        repository.update_process_state(identity, "success")

    repository.close()


def test_sqlite_repository_list_all_returns_records(tmp_path: Path) -> None:
    repository = SQLiteDownloadRecordRepository(tmp_path)

    first_record = DownloadRecord(
        name="first.csv",
        remote_path="/remote/incoming/first.csv",
        local_path="/data/downloads/first.csv",
        size=123,
        mtime=1719230000,
        process_state="pending",
    )

    second_record = DownloadRecord(
        name="second.csv",
        remote_path="/remote/incoming/second.csv",
        local_path="/data/downloads/second.csv",
        size=456,
        mtime=1719230001,
        process_state="success",
    )

    repository.save(first_record)
    repository.save(second_record)

    assert repository.list_all() == [
        first_record,
        second_record,
    ]

    repository.close()


def test_sqlite_repository_list_by_process_state_returns_matching_records(
    tmp_path: Path,
) -> None:
    repository = SQLiteDownloadRecordRepository(tmp_path)

    pending_record = DownloadRecord(
        name="pending.csv",
        remote_path="/remote/incoming/pending.csv",
        local_path="/data/downloads/pending.csv",
        size=123,
        mtime=1719230000,
        process_state="pending",
    )

    success_record = DownloadRecord(
        name="success.csv",
        remote_path="/remote/incoming/success.csv",
        local_path="/data/downloads/success.csv",
        size=456,
        mtime=1719230001,
        process_state="success",
    )

    failed_record = DownloadRecord(
        name="failed.csv",
        remote_path="/remote/incoming/failed.csv",
        local_path="/data/downloads/failed.csv",
        size=789,
        mtime=1719230002,
        process_state="failed",
    )

    repository.save(pending_record)
    repository.save(success_record)
    repository.save(failed_record)

    assert repository.list_by_process_state("pending") == [pending_record]
    assert repository.list_by_process_state("success") == [success_record]
    assert repository.list_by_process_state("failed") == [failed_record]

    repository.close()


def test_sqlite_repository_persists_across_instances(tmp_path: Path) -> None:
    record = DownloadRecord(
        name="report.csv",
        remote_path="/remote/incoming/report.csv",
        local_path="/data/downloads/report.csv",
        size=123,
        mtime=1719230000,
        process_state="pending",
    )

    first_repository = SQLiteDownloadRecordRepository(tmp_path)
    first_repository.save(record)
    first_repository.close()

    second_repository = SQLiteDownloadRecordRepository(tmp_path)

    assert second_repository.get(record.identity) == record

    second_repository.close()


def test_sqlite_repository_treats_same_path_different_size_as_different_record(
    tmp_path: Path,
) -> None:
    repository = SQLiteDownloadRecordRepository(tmp_path)

    first_record = DownloadRecord(
        name="report.csv",
        remote_path="/remote/incoming/report.csv",
        local_path="/data/downloads/report.csv",
        size=123,
        mtime=1719230000,
        process_state="pending",
    )

    second_record = DownloadRecord(
        name="report.csv",
        remote_path="/remote/incoming/report.csv",
        local_path="/data/downloads/report.csv",
        size=456,
        mtime=1719230000,
        process_state="pending",
    )

    repository.save(first_record)
    repository.save(second_record)

    assert len(repository.list_all()) == 2

    repository.close()


def test_sqlite_repository_treats_same_path_different_mtime_as_different_record(
    tmp_path: Path,
) -> None:
    repository = SQLiteDownloadRecordRepository(tmp_path)

    first_record = DownloadRecord(
        name="report.csv",
        remote_path="/remote/incoming/report.csv",
        local_path="/data/downloads/report.csv",
        size=123,
        mtime=1719230000,
        process_state="pending",
    )

    second_record = DownloadRecord(
        name="report.csv",
        remote_path="/remote/incoming/report.csv",
        local_path="/data/downloads/report.csv",
        size=123,
        mtime=1719239999,
        process_state="pending",
    )

    repository.save(first_record)
    repository.save(second_record)

    assert len(repository.list_all()) == 2

    repository.close()


def test_sqlite_repository_enables_wal_mode(tmp_path: Path) -> None:
    repository = SQLiteDownloadRecordRepository(tmp_path)

    journal_mode = repository._connection.execute(  # type: ignore
        "PRAGMA journal_mode"
    ).fetchone()

    assert journal_mode is not None
    assert str(journal_mode[0]).lower() == "wal"

    repository.close()


def test_sqlite_repository_configures_30_second_busy_timeout(tmp_path: Path) -> None:
    repository = SQLiteDownloadRecordRepository(tmp_path)

    busy_timeout = repository._connection.execute(  # type: ignore
        "PRAGMA busy_timeout"
    ).fetchone()

    assert busy_timeout is not None
    assert int(busy_timeout[0]) == 30_000

    repository.close()
