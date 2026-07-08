from sftp_watcher.state_store.models import (
    DownloadRecord,
    FileIdentity,
    ProcessState,
)
from sftp_watcher.state_store.service import DownloadStateService


class InMemoryDownloadRecordRepository:
    def __init__(self) -> None:
        self.records: dict[FileIdentity, DownloadRecord] = {}

    def exists(self, identity: FileIdentity) -> bool:
        return identity in self.records

    def get(self, identity: FileIdentity) -> DownloadRecord | None:
        return self.records.get(identity)

    def save(self, record: DownloadRecord) -> None:
        self.records[record.identity] = record

    def update_process_state(
        self,
        identity: FileIdentity,
        process_state: ProcessState,
    ) -> None:
        existing_record = self.records.get(identity)

        if existing_record is None:
            raise KeyError(f"Cannot update unknown file: {identity.remote_path}")

        self.records[identity] = existing_record.with_process_state(process_state)

    def list_all(self) -> list[DownloadRecord]:
        return list(self.records.values())

    def list_by_process_state(
        self,
        process_state: ProcessState,
    ) -> list[DownloadRecord]:
        return [
            record
            for record in self.records.values()
            if record.process_state == process_state
        ]


def test_service_already_downloaded_returns_false_when_record_does_not_exist() -> None:
    repository = InMemoryDownloadRecordRepository()
    service = DownloadStateService(repository)

    record = DownloadRecord(
        name="report.csv",
        remote_path="/remote/incoming/report.csv",
        local_path="/data/downloads/report.csv",
        size=123,
        mtime=1719230000,
    )

    assert service.already_downloaded(record) is False


def test_service_mark_downloaded_saves_record_as_pending() -> None:
    repository = InMemoryDownloadRecordRepository()
    service = DownloadStateService(repository)

    record = DownloadRecord(
        name="report.csv",
        remote_path="/remote/incoming/report.csv",
        local_path="/data/downloads/report.csv",
        size=123,
        mtime=1719230000,
        process_state="success",
    )

    service.mark_downloaded(record)

    saved_record = repository.get(record.identity)

    assert saved_record is not None
    assert saved_record.process_state == "pending"


def test_service_mark_downloaded_does_not_overwrite_existing_record() -> None:
    repository = InMemoryDownloadRecordRepository()
    service = DownloadStateService(repository)

    record = DownloadRecord(
        name="report.csv",
        remote_path="/remote/incoming/report.csv",
        local_path="/data/downloads/report.csv",
        size=123,
        mtime=1719230000,
        process_state="pending",
    )

    existing_record = record.with_process_state("success")

    repository.save(existing_record)

    service.mark_downloaded(record)

    saved_record = repository.get(record.identity)

    assert saved_record == existing_record


def test_service_mark_success_updates_process_state() -> None:
    repository = InMemoryDownloadRecordRepository()
    service = DownloadStateService(repository)

    record = DownloadRecord(
        name="report.csv",
        remote_path="/remote/incoming/report.csv",
        local_path="/data/downloads/report.csv",
        size=123,
        mtime=1719230000,
    )

    repository.save(record)

    service.mark_success(record.identity)

    saved_record = repository.get(record.identity)

    assert saved_record is not None
    assert saved_record.process_state == "success"


def test_service_mark_failed_updates_process_state() -> None:
    repository = InMemoryDownloadRecordRepository()
    service = DownloadStateService(repository)

    record = DownloadRecord(
        name="report.csv",
        remote_path="/remote/incoming/report.csv",
        local_path="/data/downloads/report.csv",
        size=123,
        mtime=1719230000,
    )

    repository.save(record)

    service.mark_failed(record.identity)

    saved_record = repository.get(record.identity)

    assert saved_record is not None
    assert saved_record.process_state == "failed"


def test_service_list_pending_returns_pending_records() -> None:
    repository = InMemoryDownloadRecordRepository()
    service = DownloadStateService(repository)

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

    repository.save(pending_record)
    repository.save(success_record)

    assert service.list_pending() == [pending_record]


def test_service_list_success_returns_success_records() -> None:
    repository = InMemoryDownloadRecordRepository()
    service = DownloadStateService(repository)

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

    repository.save(pending_record)
    repository.save(success_record)

    assert service.list_success() == [success_record]


def test_service_list_failed_returns_failed_records() -> None:
    repository = InMemoryDownloadRecordRepository()
    service = DownloadStateService(repository)

    failed_record = DownloadRecord(
        name="failed.csv",
        remote_path="/remote/incoming/failed.csv",
        local_path="/data/downloads/failed.csv",
        size=123,
        mtime=1719230000,
        process_state="failed",
    )

    success_record = DownloadRecord(
        name="success.csv",
        remote_path="/remote/incoming/success.csv",
        local_path="/data/downloads/success.csv",
        size=456,
        mtime=1719230001,
        process_state="success",
    )

    repository.save(failed_record)
    repository.save(success_record)

    assert service.list_failed() == [failed_record]
