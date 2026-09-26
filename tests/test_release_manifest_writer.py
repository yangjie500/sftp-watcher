import json
from pathlib import Path

import pytest

from sftp_watcher.bundle.release_manifest_writer import ReleaseManifestWriter


def test_release_manifest_writer_writes_release_json(tmp_path: Path) -> None:
    manifest_path = ReleaseManifestWriter().write(
        directory=tmp_path,
        tenant_id="mario",
        project_name="frontend",
        project_version="22.0.7",
        remote_tarball_path=(
            "upload/mario-+frontend-+22.0.7-+20241028T115959.tar.gz.bundle"
        ),
    )

    assert manifest_path == tmp_path / "release.json"
    assert json.loads(manifest_path.read_text(encoding="utf-8")) == {
        "tenant_id": "mario",
        "project_name": "frontend",
        "project_version": "22.0.7",
        "remote_tarball_path": (
            "upload/mario-+frontend-+22.0.7-+20241028T115959.tar.gz.bundle"
        ),
    }


def test_release_manifest_writer_rejects_missing_directory(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="does not exist"):
        ReleaseManifestWriter().write(
            directory=tmp_path / "missing",
            tenant_id="mario",
            project_name="frontend",
            project_version="22.0.7",
            remote_tarball_path="upload/bundle.tar.gz.bundle",
        )


def test_release_manifest_writer_rejects_file_path(tmp_path: Path) -> None:
    path = tmp_path / "not-a-directory"
    path.write_text("content", encoding="utf-8")

    with pytest.raises(ValueError, match="not a directory"):
        ReleaseManifestWriter().write(
            directory=path,
            tenant_id="mario",
            project_name="frontend",
            project_version="22.0.7",
            remote_tarball_path="upload/bundle.tar.gz.bundle",
        )
