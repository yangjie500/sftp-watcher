from pathlib import Path

from sftp_watcher.bundle.models import (
    BundleExtractionResult,
    BundleFilterResult,
    HelmChartExpansionResult,
    PreparedBundleRequest,
    PreparedBundleResult,
)


def test_bundle_models_are_constructable() -> None:
    extraction = BundleExtractionResult(
        outer_bundle_path=Path("outer.tar.gz.bundle"),
        nested_bundle_path=Path("nested.tar.gz"),
        extracted_dir=Path("extracted"),
    )
    filter_result = BundleFilterResult(
        removed_paths=(Path("extracted/images/logo.png"),),
        remaining_paths=(Path("extracted/charts/Chart.yaml"),),
    )
    chart_expansion_result = HelmChartExpansionResult(
        expanded_charts=(Path("extracted/frontend"),),
        removed_packages=(Path("extracted/frontend-1.2.3.tgz"),),
    )
    publish_request = PreparedBundleRequest(
        source_dir=Path("extracted"),
        tenant_id="tenant-a",
        project_name="frontend",
        project_version="1.2.3",
        remote_tarball_path="upload/bundle.tar.gz",
        bundle_name="bundle.tar.gz",
    )
    publish_result = PreparedBundleResult(
        handled=True,
        changed_file_count=1,
        target="https://gitlab.example.com/group/repo.git",
        branch="main",
        commit_sha="abc123",
    )

    assert extraction.nested_bundle_path == Path("nested.tar.gz")
    assert filter_result.removed_paths == (Path("extracted/images/logo.png"),)
    assert chart_expansion_result.expanded_charts == (Path("extracted/frontend"),)
    assert publish_request.tenant_id == "tenant-a"
    assert publish_result.target == "https://gitlab.example.com/group/repo.git"
