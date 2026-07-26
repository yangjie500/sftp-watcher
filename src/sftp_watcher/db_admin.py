from argparse import ArgumentParser, Namespace
from collections.abc import Callable, Sequence
from pathlib import Path

from sftp_watcher.state_store import (
    DownloadRecord,
    DownloadStateService,
    FileIdentity,
    ProcessState,
    SQLiteDownloadRecordRepository,
)


def main(args: Sequence[str] | None = None) -> None:
    parser = _build_parser()
    parsed = parser.parse_args(args)

    repository = SQLiteDownloadRecordRepository(local_dir=parsed.db_dir)

    try:
        service = DownloadStateService(repository)
        parsed.handler(parsed, service)
    finally:
        repository.close()


def _build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        prog="sftp-watcher-db",
        description="Inspect and update the SFTP watcher SQLite state database.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List download records")
    list_parser.add_argument("--db-dir", type=Path, required=True)
    list_parser.add_argument(
        "--state",
        choices=("pending", "success", "failed"),
        default=None,
    )
    list_parser.set_defaults(handler=_handle_list)

    for state in ("pending", "success", "failed"):
        command = f"mark-{state}"
        update_parser = subparsers.add_parser(
            command,
            help=f"Mark a download record as {state}",
        )
        update_parser.add_argument("--db-dir", type=Path, required=True)
        update_parser.add_argument("--remote-path", required=True)
        update_parser.add_argument("--size", type=int, required=True)
        update_parser.add_argument("--mtime", type=int, required=True)
        update_parser.set_defaults(handler=_make_update_handler(state))

    return parser


def _handle_list(parsed: Namespace, service: DownloadStateService) -> None:
    if parsed.state is None:
        records = service.list_all()
    elif parsed.state == "pending":
        records = service.list_pending()
    elif parsed.state == "success":
        records = service.list_success()
    else:
        records = service.list_failed()

    _print_records(records)


def _make_update_handler(
    process_state: ProcessState,
) -> Callable[[Namespace, DownloadStateService], None]:
    def handler(parsed: Namespace, service: DownloadStateService) -> None:
        identity = FileIdentity(
            remote_path=parsed.remote_path,
            size=parsed.size,
            mtime=parsed.mtime,
        )

        try:
            if process_state == "pending":
                service.mark_pending(identity)
            elif process_state == "success":
                service.mark_success(identity)
            else:
                service.mark_failed(identity)
        except KeyError as error:
            raise SystemExit(str(error)) from error

        print(
            "Updated record: "
            f"remote_path={identity.remote_path} "
            f"size={identity.size} "
            f"mtime={identity.mtime} "
            f"process_state={process_state}"
        )

    return handler


def _print_records(records: list[DownloadRecord]) -> None:
    print("process_state\tremote_path\tsize\tmtime\tlocal_path")

    for record in records:
        print(
            f"{record.process_state}\t"
            f"{record.remote_path}\t"
            f"{record.size}\t"
            f"{record.mtime}\t"
            f"{record.local_path}"
        )


if __name__ == "__main__":
    main()
