from pathlib import Path

import pytest

from sftp_watcher.processor.bundle_content_filter import (
    ContainerImageRemovingBundleContentFilter,
)


def test_filter_removes_container_image_directories(tmp_path: Path) -> None:
    bundle_dir = tmp_path / "bundle"
    _write_file(bundle_dir / "charts/app/Chart.yaml", "apiVersion: v2\n")
    _write_file(bundle_dir / "metadata/release.json", "{}\n")
    _write_file(bundle_dir / "images/app.tar", "image archive")
    _write_file(bundle_dir / "container-images/db.tar.gz", "image archive")

    result = ContainerImageRemovingBundleContentFilter().filter(bundle_dir)

    assert not (bundle_dir / "images").exists()
    assert not (bundle_dir / "container-images").exists()
    assert (bundle_dir / "charts/app/Chart.yaml").exists()
    assert (bundle_dir / "metadata/release.json").exists()
    assert result.removed_paths == (
        bundle_dir / "images/app.tar",
        bundle_dir / "images",
        bundle_dir / "container-images/db.tar.gz",
        bundle_dir / "container-images",
    )
    assert result.remaining_paths == (
        bundle_dir / "charts/app/Chart.yaml",
        bundle_dir / "metadata/release.json",
    )


def test_filter_does_not_remove_helm_chart_tgz_outside_image_dir(
    tmp_path: Path,
) -> None:
    bundle_dir = tmp_path / "bundle"
    _write_file(bundle_dir / "charts/app-1.0.0.tgz", "helm chart package")
    _write_file(bundle_dir / "metadata/release.json", "{}\n")

    result = ContainerImageRemovingBundleContentFilter().filter(bundle_dir)

    assert (bundle_dir / "charts/app-1.0.0.tgz").exists()
    assert result.removed_paths == ()
    assert result.remaining_paths == (
        bundle_dir / "charts/app-1.0.0.tgz",
        bundle_dir / "metadata/release.json",
    )


def test_filter_supports_custom_container_image_dirs(tmp_path: Path) -> None:
    bundle_dir = tmp_path / "bundle"
    _write_file(bundle_dir / "offline-images/app.tar", "image archive")
    _write_file(bundle_dir / "charts/app/Chart.yaml", "apiVersion: v2\n")

    result = ContainerImageRemovingBundleContentFilter(
        container_image_dirs=("offline-images",)
    ).filter(bundle_dir)

    assert not (bundle_dir / "offline-images").exists()
    assert result.removed_paths == (
        bundle_dir / "offline-images/app.tar",
        bundle_dir / "offline-images",
    )


def test_filter_rejects_missing_directory(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="does not exist"):
        ContainerImageRemovingBundleContentFilter().filter(tmp_path / "missing")


def test_filter_rejects_file_path(tmp_path: Path) -> None:
    file_path = tmp_path / "bundle"
    file_path.write_text("not a directory")

    with pytest.raises(ValueError, match="not a directory"):
        ContainerImageRemovingBundleContentFilter().filter(file_path)


def _write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
