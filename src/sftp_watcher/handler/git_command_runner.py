import os
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class GitCommandResult:
    command: tuple[str, ...]
    cwd: Path | None
    stdout: str
    stderr: str


class GitCommandError(RuntimeError):
    def __init__(
        self,
        *,
        command: Sequence[str],
        cwd: Path | None,
        returncode: int | None,
        stdout: str,
        stderr: str,
        message: str,
    ) -> None:
        self.command = tuple(command)
        self.cwd = cwd
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr

        super().__init__(message)


class GitCommandRunner:
    def __init__(
        self,
        *,
        timeout_seconds: int = 60,
        secrets: Sequence[str] = (),
    ) -> None:
        self._timeout_seconds = timeout_seconds
        self._secrets = tuple(secret for secret in secrets if secret)

    def run(
        self,
        args: Sequence[str],
        *,
        cwd: Path | None = None,
        extra_env: Mapping[str, str] | None = None,
    ) -> GitCommandResult:
        command = ("git", *args)
        env = os.environ.copy()

        env.update(
            {
                "GIT_TERMINAL_PROMPT": "0",
                "GIT_ASKPASS": "",
                "GCM_INTERACTIVE": "never",
            }
        )

        if extra_env is not None:
            env.update(extra_env)

        try:
            completed = subprocess.run(
                command,
                cwd=cwd,
                env=env,
                text=True,
                capture_output=True,
                timeout=self._timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as error:
            masked_command = self._mask_command(command)
            stdout = self._mask_string(self._string_output(error.stdout))
            stderr = self._mask_string(self._string_output(error.stderr))
            raise GitCommandError(
                command=masked_command,
                cwd=cwd,
                returncode=None,
                stdout=stdout,
                stderr=stderr,
                message=(
                    "Git command timed out: "
                    f"command={masked_command} cwd={cwd} "
                    f"timeout_seconds={self._timeout_seconds}"
                ),
            ) from error

        stdout = self._mask_string(completed.stdout)
        stderr = self._mask_string(completed.stderr)

        if completed.returncode != 0:
            masked_command = self._mask_command(command)
            raise GitCommandError(
                command=masked_command,
                cwd=cwd,
                returncode=completed.returncode,
                stdout=stdout,
                stderr=stderr,
                message=(
                    "Git command failed: "
                    f"command={masked_command} cwd={cwd} "
                    f"returncode={completed.returncode} stderr={stderr}"
                ),
            )

        return GitCommandResult(
            command=command,
            cwd=cwd,
            stdout=stdout,
            stderr=stderr,
        )

    def _mask_string(self, value: str) -> str:
        masked_value = value

        for secret in self._secrets:
            masked_value = masked_value.replace(secret, "<redacted>")

        return masked_value

    def _mask_command(self, command: Sequence[str]) -> tuple[str, ...]:
        return tuple(self._mask_string(item) for item in command)

    def _string_output(self, value: bytes | str | None) -> str:
        if value is None:
            return ""

        if isinstance(value, bytes):
            return value.decode(errors="replace")

        return value
