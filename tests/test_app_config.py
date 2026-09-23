import os
from pathlib import Path
from unittest.mock import patch

from sftp_watcher.config import AppConfig


def test_app_config_loads_env_file_once(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "SFTP_HOST=sftp.example.com",
                "SFTP_PORT=2222",
                "SFTP_USERNAME=sftp-user",
                "SFTP_PASSWORD=sftp-password",
                "SFTP_REMOTE_DIR=upload",
                f"SFTP_LOCAL_DIR={tmp_path / 'downloads'}",
                f"SFTP_STATE_STORE_DIR={tmp_path / 'state'}",
                "GIT_REMOTE_URL=https://gitlab.example.com/group/repo.git",
                "GIT_BRANCH=main",
                "BUNDLE_FILENAME_METADATA_SEPARATOR=__",
                "BUNDLE_CONTAINER_IMAGE_DIRS=offline-images,image-archives",
            ]
        )
    )

    with patch.dict(os.environ, {}, clear=True):
        config = AppConfig.from_env(env_file)

        assert config.sftp.host == "sftp.example.com"
        assert config.sftp.port == 2222
        assert config.git.remote_url == "https://gitlab.example.com/group/repo.git"
        assert config.bundle.filename_metadata_separator == "__"
        assert config.bundle.container_image_dirs == (
            "offline-images",
            "image-archives",
        )
