import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from sftp_watcher.handler.git_command_runner import (
    GitCommandError,
    GitCommandRunner,
)


def test_run_returns_git_command_result(tmp_path: Path) -> None:
    completed = subprocess.CompletedProcess(
        args=("git", "status", "--short"),
        returncode=0,
        stdout="clean\n",
        stderr="",
    )

    with patch(
        "sftp_watcher.handler.git_command_runner.subprocess.run",
        return_value=completed,
    ) as run:
        result = GitCommandRunner(timeout_seconds=30).run(
            ("status", "--short"),
            cwd=tmp_path,
            extra_env={"GIT_TERMINAL_PROMPT": "0"},
        )

    run.assert_called_once_with(
        ("git", "status", "--short"),
        cwd=tmp_path,
        env=run.call_args.kwargs["env"],
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    assert run.call_args.kwargs["env"]["GIT_TERMINAL_PROMPT"] == "0"
    assert result.command == ("git", "status", "--short")
    assert result.cwd == tmp_path
    assert result.stdout == "clean\n"
    assert result.stderr == ""


def test_run_raises_error_and_masks_secret_on_failure(tmp_path: Path) -> None:
    completed = subprocess.CompletedProcess(
        args=("git", "clone"),
        returncode=128,
        stdout="token-secret in stdout",
        stderr="failed with token-secret",
    )

    with patch(
        "sftp_watcher.handler.git_command_runner.subprocess.run",
        return_value=completed,
    ):
        with pytest.raises(GitCommandError) as error:
            GitCommandRunner(secrets=("token-secret",)).run(
                ("clone", "https://token-secret@gitlab.example.com/group/repo.git"),
                cwd=tmp_path,
            )

    assert error.value.returncode == 128
    assert "token-secret" not in str(error.value)
    assert "token-secret" not in error.value.stdout
    assert "token-secret" not in error.value.stderr
    assert "token-secret" not in " ".join(error.value.command)
    assert "<redacted>" in str(error.value)


def test_run_raises_error_and_masks_secret_on_timeout(tmp_path: Path) -> None:
    timeout = subprocess.TimeoutExpired(
        cmd=("git", "push", "https://token-secret@gitlab.example.com/group/repo.git"),
        timeout=5,
        output=b"token-secret in stdout",
        stderr=b"token-secret in stderr",
    )

    with patch(
        "sftp_watcher.handler.git_command_runner.subprocess.run",
        side_effect=timeout,
    ):
        with pytest.raises(GitCommandError) as error:
            GitCommandRunner(timeout_seconds=5, secrets=("token-secret",)).run(
                ("push", "origin", "main"),
                cwd=tmp_path,
            )

    assert error.value.returncode is None
    assert "token-secret" not in str(error.value)
    assert "token-secret" not in error.value.stdout
    assert "token-secret" not in error.value.stderr
    assert "<redacted>" in error.value.stdout
    assert "<redacted>" in error.value.stderr
