import io
import tarfile
from pathlib import Path

import pytest

from sftp_watcher.processor.bundle_extractor import SafeTarBundleExtractor


def test_extracts_outer_bundle_and_nested_tarball(tmp_path: Path) -> None:
    bundle_path = tmp_path / "release.tar.gz.bundle"
    nested_tarball = _tarball_bytes(
        {
            "charts/app/Chart.yaml": "apiVersion: v2\nname: app\n",
            "metadata/release.json": "{}\n",
        }
    )
    _write_tarball(
        bundle_path,
        {
            "payload/release.tar.gz": nested_tarball,
            "payload/release.tar.gz.sig": b"signature",
        },
    )

    destination_dir = tmp_path / "work"

    result = SafeTarBundleExtractor().extract(bundle_path, destination_dir)

    assert result.outer_bundle_path == bundle_path
    assert result.nested_bundle_path == destination_dir / "outer/payload/release.tar.gz"
    assert result.extracted_dir == destination_dir / "extracted"
    assert (result.extracted_dir / "charts/app/Chart.yaml").read_text() == (
        "apiVersion: v2\nname: app\n"
    )
    assert (result.extracted_dir / "metadata/release.json").read_text() == "{}\n"


def test_extract_rejects_unsafe_outer_tar_path(tmp_path: Path) -> None:
    bundle_path = tmp_path / "release.tar.gz.bundle"
    _write_tarball(bundle_path, {"../escape.txt": b"unsafe"})

    with pytest.raises(ValueError, match="Unsafe path detected"):
        SafeTarBundleExtractor().extract(bundle_path, tmp_path / "work")


def test_extract_rejects_unsafe_nested_tar_path(tmp_path: Path) -> None:
    bundle_path = tmp_path / "release.tar.gz.bundle"
    nested_tarball = _tarball_bytes({"../escape.txt": b"unsafe"})
    _write_tarball(
        bundle_path,
        {
            "payload/release.tar.gz": nested_tarball,
            "payload/release.tar.gz.sig": b"signature",
        },
    )

    with pytest.raises(ValueError, match="Unsafe path detected"):
        SafeTarBundleExtractor().extract(bundle_path, tmp_path / "work")


def test_extract_requires_signature_file(tmp_path: Path) -> None:
    bundle_path = tmp_path / "release.tar.gz.bundle"
    _write_tarball(bundle_path, {"payload/release.tar.gz": _tarball_bytes({})})

    with pytest.raises(FileNotFoundError, match="signature file"):
        SafeTarBundleExtractor().extract(bundle_path, tmp_path / "work")


def test_extract_requires_nested_tarball_next_to_signature(tmp_path: Path) -> None:
    bundle_path = tmp_path / "release.tar.gz.bundle"
    _write_tarball(bundle_path, {"payload/release.tar.gz.sig": b"signature"})

    with pytest.raises(FileNotFoundError, match="nested tarball"):
        SafeTarBundleExtractor().extract(bundle_path, tmp_path / "work")


def test_extract_rejects_multiple_nested_tarball_candidates(tmp_path: Path) -> None:
    bundle_path = tmp_path / "release.tar.gz.bundle"
    _write_tarball(
        bundle_path,
        {
            "payload/first.tar.gz": _tarball_bytes({}),
            "payload/second.tar.gz": _tarball_bytes({}),
            "payload/release.sig": b"signature",
        },
    )

    with pytest.raises(ValueError, match="multiple nested tarball candidates"):
        SafeTarBundleExtractor().extract(bundle_path, tmp_path / "work")


def _write_tarball(tarball_path: Path, files: dict[str, bytes]) -> None:
    with tarfile.open(tarball_path, "w:gz") as tar:
        for name, content in files.items():
            _add_tar_member(tar, name, content)


def _tarball_bytes(files: dict[str, str | bytes]) -> bytes:
    buffer = io.BytesIO()

    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for name, content in files.items():
            data = content.encode("utf-8") if isinstance(content, str) else content
            _add_tar_member(tar, name, data)

    return buffer.getvalue()


def _add_tar_member(tar: tarfile.TarFile, name: str, content: bytes) -> None:
    tar_info = tarfile.TarInfo(name=name)
    tar_info.size = len(content)
    tar.addfile(tar_info, io.BytesIO(content))
