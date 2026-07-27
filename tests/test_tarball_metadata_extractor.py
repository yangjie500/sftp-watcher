import io
import json
import tarfile
from pathlib import Path

import pytest

from sftp_watcher.processor.tarball_metadata_extractor import TarballMetadataExtractor


def test_extract_tarball_metadata_returns_derived_fields(tmp_path: Path) -> None:
    tarball_path = tmp_path / "release.tar.gz.bundle"
    _write_tarball(
        tarball_path,
        {
            "TIMESTAMP.json": json.dumps(
                {
                    "SIZEOFFILE": "2048 KB",
                    "TIMEDATE": "20241028T115959",
                }
            )
        },
    )

    metadata = TarballMetadataExtractor().extract(tarball_path)

    assert metadata["tarball_name"] == "release.tar.gz.bundle"
    assert metadata["SIZEOFFILE"] == "2048 KB"
    assert metadata["TIMEDATE"] == "20241028T115959"
    assert metadata["SIZE_KB"] == 2048.0
    assert metadata["SIZE_MB"] == 2.0
    assert metadata["SIZE_GB"] == 0.002
    assert metadata["TIME_TAKEN_SECONDS"] >= 0


def test_extract_tarball_metadata_rejects_missing_metadata_file(
    tmp_path: Path,
) -> None:
    tarball_path = tmp_path / "release.tar.gz.bundle"
    _write_tarball(tarball_path, {"README.txt": "hello"})

    with pytest.raises(FileNotFoundError, match="does not contain TIMESTAMP.json"):
        TarballMetadataExtractor().extract(tarball_path)


def test_extract_tarball_metadata_rejects_invalid_timestamp(
    tmp_path: Path,
) -> None:
    tarball_path = tmp_path / "release.tar.gz.bundle"
    _write_tarball(
        tarball_path,
        {
            "TIMESTAMP.json": json.dumps(
                {
                    "SIZEOFFILE": "2048 KB",
                    "TIMEDATE": "2024-10-28 11:59:59",
                }
            )
        },
    )

    with pytest.raises(ValueError, match="Invalid TIMESTAMP format"):
        TarballMetadataExtractor().extract(tarball_path)


def test_extract_tarball_metadata_rejects_unsafe_tar_path(tmp_path: Path) -> None:
    tarball_path = tmp_path / "release.tar.gz.bundle"
    _write_tarball(
        tarball_path,
        {"../TIMESTAMP.json": json.dumps({"SIZEOFFILE": "2048 KB"})},
    )

    with pytest.raises(ValueError, match="Unsafe path detected"):
        TarballMetadataExtractor().extract(tarball_path)


def _write_tarball(tarball_path: Path, files: dict[str, str]) -> None:
    with tarfile.open(tarball_path, "w:gz") as tar:
        for name, content in files.items():
            data = content.encode("utf-8")
            tar_info = tarfile.TarInfo(name=name)
            tar_info.size = len(data)
            tar.addfile(tar_info, io.BytesIO(data))
