import io
import tarfile
from pathlib import Path

import pytest

from sftp_watcher.bundle.helm_chart_expander import PackagedHelmChartExpander


def test_expands_packaged_helm_chart_and_removes_package(tmp_path: Path) -> None:
    package_path = tmp_path / "frontend-22.0.7.tgz"
    _write_tgz(
        package_path,
        {
            "frontend/Chart.yaml": "apiVersion: v2\nname: frontend\n",
            "frontend/values.yaml": "replicaCount: 1\n",
        },
    )

    result = PackagedHelmChartExpander().expand(tmp_path)

    assert result.expanded_charts == (tmp_path / "frontend",)
    assert result.removed_packages == (package_path,)
    assert not package_path.exists()
    assert (tmp_path / "frontend/Chart.yaml").read_text(
        encoding="utf-8"
    ) == "apiVersion: v2\nname: frontend\n"
    assert (tmp_path / "frontend/values.yaml").read_text(
        encoding="utf-8"
    ) == "replicaCount: 1\n"


def test_ignores_non_helm_tgz(tmp_path: Path) -> None:
    package_path = tmp_path / "archive.tgz"
    _write_tgz(package_path, {"content/readme.txt": "not a chart\n"})

    result = PackagedHelmChartExpander().expand(tmp_path)

    assert result.expanded_charts == ()
    assert result.removed_packages == ()
    assert package_path.exists()


def test_rejects_unsafe_helm_chart_package_path(tmp_path: Path) -> None:
    package_path = tmp_path / "unsafe-chart.tgz"
    _write_tgz(package_path, {"../frontend/Chart.yaml": "apiVersion: v2\n"})

    with pytest.raises(ValueError, match="Unsafe path"):
        PackagedHelmChartExpander().expand(tmp_path)


def test_rejects_missing_expansion_directory(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="does not exist"):
        PackagedHelmChartExpander().expand(tmp_path / "missing")


def test_rejects_file_expansion_path(tmp_path: Path) -> None:
    path = tmp_path / "not-a-directory"
    path.write_text("content", encoding="utf-8")

    with pytest.raises(ValueError, match="not a directory"):
        PackagedHelmChartExpander().expand(path)


def _write_tgz(path: Path, files: dict[str, str]) -> None:
    with tarfile.open(path, mode="w:gz") as tar:
        for name, content in files.items():
            encoded = content.encode("utf-8")
            member = tarfile.TarInfo(name)
            member.size = len(encoded)
            tar.addfile(member, io.BytesIO(encoded))
