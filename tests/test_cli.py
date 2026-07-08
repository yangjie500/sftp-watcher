import subprocess
import sys

from sftp_watcher import __version__


def test_cli_version():
    cmd = [sys.executable, "-m", "sftp_watcher", "--version"]
    assert subprocess.check_output(cmd).decode().strip() == __version__
