from pathlib import Path

import pytest
from sqlalchemy import create_engine

from sftp_watcher.db_admin import main
from sftp_watcher.state_store import DownloadRecord, SQLiteDownloadRecordRepository
from sftp_watcher.state_store.models import ProcessState
from sftp_watcher.state_store.schema import metadata


def _create_schema(tmp_path: Path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'download_state.sqlite3'}")
    metadata.create_all(engine)
    engine.dispose()


def _seed_record(
    tmp_path: Path,
    *,
    process_state: ProcessState = "pending",
    name: str = "file.tar.gz.bundle",
    remote_path: str = "/remote/file.tar.gz.bundle",
    local_path: str = "/local/file.tar.gz.bundle",
    size: int = 123,
    mtime: int = 456,
) -> DownloadRecord:
    _create_schema(tmp_path)

    record = DownloadRecord(
        name=name,
        remote_path=remote_path,
        local_path=local_path,
        size=size,
        mtime=mtime,
        process_state=process_state,
    )

    repository = SQLiteDownloadRecordRepository(local_dir=tmp_path)
    try:
        repository.save(record)
    finally:
        repository.close()

    return record


def test_db_admin_list_records(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _seed_record(tmp_path)

    main(["list", "--db-dir", str(tmp_path)])

    output = capsys.readouterr().out

    assert "process_state\tremote_path\tsize\tmtime\tlocal_path" in output
    assert (
        "pending\t/remote/file.tar.gz.bundle\t123\t456\t/local/file.tar.gz.bundle"
        in output
    )


def test_db_admin_list_records_by_state(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _seed_record(tmp_path, process_state="failed")
    _seed_record(
        tmp_path,
        process_state="success",
        name="other.tar.gz.bundle",
        remote_path="/remote/other.tar.gz.bundle",
        local_path="/local/other.tar.gz.bundle",
        size=789,
        mtime=111,
    )

    main(["list", "--db-dir", str(tmp_path), "--state", "failed"])

    output = capsys.readouterr().out

    assert (
        "failed\t/remote/file.tar.gz.bundle\t123\t456\t/local/file.tar.gz.bundle"
        in output
    )
    assert "/remote/other.tar.gz.bundle" not in output


def test_db_admin_mark_pending(tmp_path: Path) -> None:
    record = _seed_record(tmp_path, process_state="failed")

    main(
        [
            "mark-pending",
            "--db-dir",
            str(tmp_path),
            "--remote-path",
            record.remote_path,
            "--size",
            str(record.size),
            "--mtime",
            str(record.mtime),
        ]
    )

    repository = SQLiteDownloadRecordRepository(local_dir=tmp_path)
    try:
        saved = repository.get(record.identity)
    finally:
        repository.close()

    assert saved is not None
    assert saved.process_state == "pending"


def test_db_admin_mark_success(tmp_path: Path) -> None:
    record = _seed_record(tmp_path, process_state="pending")

    main(
        [
            "mark-success",
            "--db-dir",
            str(tmp_path),
            "--remote-path",
            record.remote_path,
            "--size",
            str(record.size),
            "--mtime",
            str(record.mtime),
        ]
    )

    repository = SQLiteDownloadRecordRepository(local_dir=tmp_path)
    try:
        saved = repository.get(record.identity)
    finally:
        repository.close()

    assert saved is not None
    assert saved.process_state == "success"


def test_db_admin_unknown_record_exits(tmp_path: Path) -> None:
    _create_schema(tmp_path)

    with pytest.raises(SystemExit):
        main(
            [
                "mark-pending",
                "--db-dir",
                str(tmp_path),
                "--remote-path",
                "/missing.tar.gz.bundle",
                "--size",
                "1",
                "--mtime",
                "2",
            ]
        )
