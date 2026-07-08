import stat
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from sftp_watcher.sftp_client import ParamikoSFTPClient, RemoteEntry


@patch("sftp_watcher.sftp_client.paramiko.SSHClient")
def test_paramiko_sftp_client_connect_success(
    mock_ssh_client_class: Mock,
) -> None:
    fake_ssh = Mock()
    fake_sftp = Mock()

    mock_ssh_client_class.return_value = fake_ssh
    fake_ssh.open_sftp.return_value = fake_sftp

    client = ParamikoSFTPClient(
        host="example.com",
        port=22,
        username="test-user",
        password="secret",
    )

    client.connect()

    mock_ssh_client_class.assert_called_once_with()
    fake_ssh.load_system_host_keys.assert_called_once_with()
    fake_ssh.set_missing_host_key_policy.assert_called_once()
    fake_ssh.connect.assert_called_once_with(
        hostname="example.com",
        port=22,
        username="test-user",
        password="secret",
    )
    fake_ssh.open_sftp.assert_called_once_with()


@patch("sftp_watcher.sftp_client.paramiko.SSHClient")
def test_paramiko_sftp_client_list_files_success(
    mock_ssh_client_class: Mock,
) -> None:
    fake_ssh = Mock()
    fake_sftp = Mock()

    fake_entry_1 = Mock()
    fake_entry_1.filename = "file1.txt"
    fake_entry_1.st_mtime = 1234567890
    fake_entry_1.st_size = 100
    fake_entry_1.st_mode = stat.S_IFREG | 0o644

    fake_entry_2 = Mock()
    fake_entry_2.filename = "file2.txt"
    fake_entry_2.st_mtime = None
    fake_entry_2.st_size = None
    fake_entry_2.st_mode = stat.S_IFREG | 0o644

    fake_sftp.listdir_attr.return_value = [fake_entry_1, fake_entry_2]
    mock_ssh_client_class.return_value = fake_ssh
    fake_ssh.open_sftp.return_value = fake_sftp

    client = ParamikoSFTPClient(
        host="example.com",
        port=22,
        username="test-user",
        password="secret",
    )

    client.connect()
    files = client.list_files("/remote/incoming")

    assert files == [
        RemoteEntry(
            name="file1.txt",
            mtime=1234567890,
            size=100,
            path="/remote/incoming/file1.txt",
        ),
        RemoteEntry(
            name="file2.txt",
            mtime=0,
            size=0,
            path="/remote/incoming/file2.txt",
        ),
    ]

    fake_sftp.listdir_attr.assert_called_once_with("/remote/incoming")


@patch("sftp_watcher.sftp_client.paramiko.SSHClient")
def test_paramiko_sftp_client_list_files_ignores_directories(
    mock_ssh_client_class: Mock,
) -> None:
    fake_ssh = Mock()
    fake_sftp = Mock()

    fake_file = Mock()
    fake_file.filename = "file1.txt"
    fake_file.st_mtime = 1234567890
    fake_file.st_size = 100
    fake_file.st_mode = stat.S_IFREG | 0o644

    fake_directory = Mock()
    fake_directory.filename = "archive"
    fake_directory.st_mtime = 1234567890
    fake_directory.st_size = 0
    fake_directory.st_mode = stat.S_IFDIR | 0o755

    fake_sftp.listdir_attr.return_value = [fake_file, fake_directory]
    mock_ssh_client_class.return_value = fake_ssh
    fake_ssh.open_sftp.return_value = fake_sftp

    client = ParamikoSFTPClient(
        host="example.com",
        port=22,
        username="test-user",
        password="secret",
    )

    client.connect()
    files = client.list_files("/remote/incoming")

    assert files == [
        RemoteEntry(
            name="file1.txt",
            mtime=1234567890,
            size=100,
            path="/remote/incoming/file1.txt",
        ),
    ]

    fake_sftp.listdir_attr.assert_called_once_with("/remote/incoming")


def test_paramiko_sftp_client_list_files_not_connected() -> None:
    client = ParamikoSFTPClient(
        host="example.com",
        port=22,
        username="test-user",
        password="secret",
    )

    with pytest.raises(RuntimeError, match="SFTP client not connected"):
        client.list_files("/remote/incoming")


@patch("sftp_watcher.sftp_client.paramiko.SSHClient")
def test_paramiko_sftp_client_download_file_success(
    mock_ssh_client_class: Mock,
    tmp_path: Path,
) -> None:
    fake_ssh = Mock()
    fake_sftp = Mock()

    mock_ssh_client_class.return_value = fake_ssh
    fake_ssh.open_sftp.return_value = fake_sftp

    client = ParamikoSFTPClient(
        host="example.com",
        port=22,
        username="test-user",
        password="secret",
    )

    client.connect()

    local_path = tmp_path / "downloaded.txt"

    client.download_file("/remote/file.txt", local_path)

    fake_sftp.get.assert_called_once_with(
        "/remote/file.txt",
        str(local_path),
    )


@patch("sftp_watcher.sftp_client.paramiko.SSHClient")
def test_paramiko_sftp_client_delete_file_success(
    mock_ssh_client_class: Mock,
) -> None:
    fake_ssh = Mock()
    fake_sftp = Mock()

    mock_ssh_client_class.return_value = fake_ssh
    fake_ssh.open_sftp.return_value = fake_sftp

    client = ParamikoSFTPClient(
        host="example.com",
        port=22,
        username="test-user",
        password="secret",
    )

    client.connect()
    client.delete_file("/remote/file.txt")

    fake_sftp.remove.assert_called_once_with("/remote/file.txt")


@patch("sftp_watcher.sftp_client.paramiko.SSHClient")
def test_paramiko_sftp_client_read_bytes_success(
    mock_ssh_client_class: Mock,
) -> None:
    fake_ssh = Mock()
    fake_sftp = Mock()

    fake_file = Mock()
    fake_file.read.return_value = b"hello"

    fake_file_context = MagicMock()
    fake_file_context.__enter__.return_value = fake_file
    fake_file_context.__exit__.return_value = None

    fake_sftp.open.return_value = fake_file_context
    mock_ssh_client_class.return_value = fake_ssh
    fake_ssh.open_sftp.return_value = fake_sftp

    client = ParamikoSFTPClient(
        host="example.com",
        port=22,
        username="test-user",
        password="secret",
    )

    client.connect()

    data = client.read_bytes(
        remote_path="/remote/file.txt",
        size=5,
        offset=10,
    )

    assert data == b"hello"

    fake_sftp.open.assert_called_once_with("/remote/file.txt", "rb")
    fake_file.seek.assert_called_once_with(10)
    fake_file.read.assert_called_once_with(5)


@patch("sftp_watcher.sftp_client.paramiko.SSHClient")
def test_paramiko_sftp_client_read_bytes_encodes_string_result(
    mock_ssh_client_class: Mock,
) -> None:
    fake_ssh = Mock()
    fake_sftp = Mock()

    fake_file = Mock()
    fake_file.read.return_value = "hello"

    fake_file_context = MagicMock()
    fake_file_context.__enter__.return_value = fake_file
    fake_file_context.__exit__.return_value = None

    fake_sftp.open.return_value = fake_file_context
    mock_ssh_client_class.return_value = fake_ssh
    fake_ssh.open_sftp.return_value = fake_sftp

    client = ParamikoSFTPClient(
        host="example.com",
        port=22,
        username="test-user",
        password="secret",
    )

    client.connect()

    data = client.read_bytes(
        remote_path="/remote/file.txt",
        size=5,
    )

    assert data == b"hello"

    fake_sftp.open.assert_called_once_with("/remote/file.txt", "rb")
    fake_file.seek.assert_called_once_with(0)
    fake_file.read.assert_called_once_with(5)


@patch("sftp_watcher.sftp_client.paramiko.SSHClient")
def test_paramiko_sftp_client_close_success(
    mock_ssh_client_class: Mock,
) -> None:
    fake_ssh = Mock()
    fake_sftp = Mock()

    fake_ssh.open_sftp.return_value = fake_sftp
    mock_ssh_client_class.return_value = fake_ssh

    client = ParamikoSFTPClient(
        host="example.com",
        port=22,
        username="test-user",
        password="secret",
    )

    client.connect()
    client.close()

    fake_sftp.close.assert_called_once_with()
    fake_ssh.close.assert_called_once_with()


@patch("sftp_watcher.sftp_client.paramiko.SSHClient")
def test_paramiko_sftp_client_walk_success(
    mock_ssh_client_class: Mock,
) -> None:
    fake_ssh = Mock()
    fake_sftp = Mock()

    fake_root_file = Mock()
    fake_root_file.filename = "root-file.txt"
    fake_root_file.st_mtime = 111
    fake_root_file.st_size = 10
    fake_root_file.st_mode = stat.S_IFREG | 0o644

    fake_customer_dir = Mock()
    fake_customer_dir.filename = "customer-a"
    fake_customer_dir.st_mtime = 1234567890
    fake_customer_dir.st_size = 0
    fake_customer_dir.st_mode = stat.S_IFDIR | 0o755

    fake_nested_file = Mock()
    fake_nested_file.filename = "nested-file.csv"
    fake_nested_file.st_mtime = 222
    fake_nested_file.st_size = 20
    fake_nested_file.st_mode = stat.S_IFREG | 0o644

    def fake_listdir_attr(path: str) -> list[Mock]:
        entries_by_path = {
            "/remote/incoming": [
                fake_root_file,
                fake_customer_dir,
            ],
            "/remote/incoming/customer-a": [
                fake_nested_file,
            ],
        }

        return entries_by_path[path]

    fake_sftp.listdir_attr.side_effect = fake_listdir_attr

    mock_ssh_client_class.return_value = fake_ssh
    fake_ssh.open_sftp.return_value = fake_sftp

    client = ParamikoSFTPClient(
        host="example.com",
        port=22,
        username="test-user",
        password="secret",
    )

    client.connect()

    files = list(client.walk("/remote/incoming"))

    assert files == [
        RemoteEntry(
            name="root-file.txt",
            mtime=111,
            size=10,
            path="/remote/incoming/root-file.txt",
        ),
        RemoteEntry(
            name="nested-file.csv",
            mtime=222,
            size=20,
            path="/remote/incoming/customer-a/nested-file.csv",
        ),
    ]

    assert fake_sftp.listdir_attr.call_count == 2
    fake_sftp.listdir_attr.assert_any_call("/remote/incoming")
    fake_sftp.listdir_attr.assert_any_call("/remote/incoming/customer-a")


@patch("sftp_watcher.sftp_client.paramiko.SSHClient")
def test_paramiko_sftp_client_walk_respects_max_depth(
    mock_ssh_client_class: Mock,
) -> None:
    fake_ssh = Mock()
    fake_sftp = Mock()

    fake_root_file = Mock()
    fake_root_file.filename = "root-file.txt"
    fake_root_file.st_mtime = 111
    fake_root_file.st_size = 10
    fake_root_file.st_mode = stat.S_IFREG | 0o644

    fake_customer_dir = Mock()
    fake_customer_dir.filename = "customer-a"
    fake_customer_dir.st_mtime = 1234567890
    fake_customer_dir.st_size = 0
    fake_customer_dir.st_mode = stat.S_IFDIR | 0o755

    fake_customer_file = Mock()
    fake_customer_file.filename = "customer-file.txt"
    fake_customer_file.st_mtime = 222
    fake_customer_file.st_size = 20
    fake_customer_file.st_mode = stat.S_IFREG | 0o644

    fake_year_dir = Mock()
    fake_year_dir.filename = "2026"
    fake_year_dir.st_mtime = 1234567890
    fake_year_dir.st_size = 0
    fake_year_dir.st_mode = stat.S_IFDIR | 0o755

    fake_too_deep_file = Mock()
    fake_too_deep_file.filename = "too-deep.csv"
    fake_too_deep_file.st_mtime = 333
    fake_too_deep_file.st_size = 30
    fake_too_deep_file.st_mode = stat.S_IFREG | 0o644

    def fake_listdir_attr(path: str) -> list[Mock]:
        entries_by_path = {
            "/remote/incoming": [
                fake_root_file,
                fake_customer_dir,
            ],
            "/remote/incoming/customer-a": [
                fake_customer_file,
                fake_year_dir,
            ],
            "/remote/incoming/customer-a/2026": [
                fake_too_deep_file,
            ],
        }

        return entries_by_path[path]

    fake_sftp.listdir_attr.side_effect = fake_listdir_attr

    mock_ssh_client_class.return_value = fake_ssh
    fake_ssh.open_sftp.return_value = fake_sftp

    client = ParamikoSFTPClient(
        host="example.com",
        port=22,
        username="test-user",
        password="secret",
    )

    client.connect()

    files = list(client.walk("/remote/incoming", max_depth=1))

    assert files == [
        RemoteEntry(
            name="root-file.txt",
            mtime=111,
            size=10,
            path="/remote/incoming/root-file.txt",
        ),
        RemoteEntry(
            name="customer-file.txt",
            mtime=222,
            size=20,
            path="/remote/incoming/customer-a/customer-file.txt",
        ),
    ]

    assert fake_sftp.listdir_attr.call_count == 2
    fake_sftp.listdir_attr.assert_any_call("/remote/incoming")
    fake_sftp.listdir_attr.assert_any_call("/remote/incoming/customer-a")

    called_paths = [call.args[0] for call in fake_sftp.listdir_attr.call_args_list]
    assert "/remote/incoming/customer-a/2026" not in called_paths
