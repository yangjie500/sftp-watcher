import os
import time
from pathlib import Path

from sftp_watcher.lifecycles.lifecycle import PollLifecycleContext
from sftp_watcher.lifecycles.local_file_cleanup import LocalFileCleanupLifecycle


def test_local_file_cleanup_lifecycle_deletes_old_files(tmp_path: Path) -> None:
    old_file = tmp_path / "old-file.txt"
    new_file = tmp_path / "new-file.txt"

    old_file.write_text("old")
    new_file.write_text("new")

    now = time.time()

    old_file_time = now - (31 * 24 * 60 * 60)
    new_file_time = now

    os.utime(old_file, (old_file_time, old_file_time))
    os.utime(new_file, (new_file_time, new_file_time))

    lifecycle = LocalFileCleanupLifecycle(
        local_dir=tmp_path,
        retention_days=30,
        cleanup_interval_seconds=3600,
        enabled=True,
    )

    context = PollLifecycleContext(
        remote_dir="/remote/incoming",
        local_dir=tmp_path,
    )

    lifecycle.after_poll(context)

    assert not old_file.exists()
    assert new_file.exists()


def test_local_file_cleanup_lifecycle_does_nothing_when_disabled(
    tmp_path: Path,
) -> None:
    old_file = tmp_path / "old-file.txt"
    old_file.write_text("old")

    now = time.time()
    old_file_time = now - (31 * 24 * 60 * 60)
    os.utime(old_file, (old_file_time, old_file_time))

    lifecycle = LocalFileCleanupLifecycle(
        local_dir=tmp_path,
        retention_days=30,
        cleanup_interval_seconds=3600,
        enabled=False,
    )

    context = PollLifecycleContext(
        remote_dir="/remote/incoming",
        local_dir=tmp_path,
    )

    lifecycle.after_poll(context)

    assert old_file.exists()


def test_local_file_cleanup_lifecycle_skips_tmp_files(tmp_path: Path) -> None:
    old_tmp_file = tmp_path / "download.tar.gz.tmp"
    old_tmp_file.write_text("partial download")

    now = time.time()
    old_file_time = now - (31 * 24 * 60 * 60)
    os.utime(old_tmp_file, (old_file_time, old_file_time))

    lifecycle = LocalFileCleanupLifecycle(
        local_dir=tmp_path,
        retention_days=30,
        cleanup_interval_seconds=3600,
        enabled=True,
    )

    context = PollLifecycleContext(
        remote_dir="/remote/incoming",
        local_dir=tmp_path,
    )

    lifecycle.after_poll(context)

    assert old_tmp_file.exists()


def test_local_file_cleanup_lifecycle_respects_cleanup_interval(
    tmp_path: Path,
) -> None:
    first_old_file = tmp_path / "first-old-file.txt"
    second_old_file = tmp_path / "second-old-file.txt"

    first_old_file.write_text("old")
    second_old_file.write_text("old")

    now = time.time()
    old_file_time = now - (31 * 24 * 60 * 60)

    os.utime(first_old_file, (old_file_time, old_file_time))
    os.utime(second_old_file, (old_file_time, old_file_time))

    lifecycle = LocalFileCleanupLifecycle(
        local_dir=tmp_path,
        retention_days=30,
        cleanup_interval_seconds=3600,
        enabled=True,
    )

    context = PollLifecycleContext(
        remote_dir="/remote/incoming",
        local_dir=tmp_path,
    )

    lifecycle.after_poll(context)

    assert not first_old_file.exists()
    assert not second_old_file.exists()

    third_old_file = tmp_path / "third-old-file.txt"
    third_old_file.write_text("old")
    os.utime(third_old_file, (old_file_time, old_file_time))

    lifecycle.after_poll(context)

    assert third_old_file.exists()


def test_local_file_cleanup_lifecycle_deletes_old_nested_files(
    tmp_path: Path,
) -> None:
    nested_dir = tmp_path / "customer-a" / "2026"
    nested_dir.mkdir(parents=True)

    old_nested_file = nested_dir / "package.tar.gz"
    old_nested_file.write_text("old tarball")

    now = time.time()
    old_file_time = now - (31 * 24 * 60 * 60)
    os.utime(old_nested_file, (old_file_time, old_file_time))

    lifecycle = LocalFileCleanupLifecycle(
        local_dir=tmp_path,
        retention_days=30,
        cleanup_interval_seconds=3600,
        enabled=True,
    )

    context = PollLifecycleContext(
        remote_dir="/remote/incoming",
        local_dir=tmp_path,
    )

    lifecycle.after_poll(context)

    assert not old_nested_file.exists()
