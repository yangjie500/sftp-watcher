"""Interface for ``python -m sftp_watcher``."""

from argparse import ArgumentParser
from collections.abc import Sequence
from pathlib import Path

from sftp_watcher.app import start_application

from . import __version__

__all__ = ["main"]


def main(args: Sequence[str] | None = None) -> None:
    """Argument parser for the CLI."""
    parser = ArgumentParser()

    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=__version__,
    )

    parser.add_argument(
        "--env-file",
        type=Path,
        dest="env_file",
        action="store",
        default=Path(".env"),
        help="Path to the environment file",
    )

    parsed = parser.parse_args(args)

    start_application(parsed.env_file)


if __name__ == "__main__":
    main()
