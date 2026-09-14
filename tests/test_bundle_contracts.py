from pathlib import Path

from sftp_watcher.processor.bundle_models import (
    BundleExtractionResult,
    BundleFilterResult,
    HelmChartExpansionResult,
    PublishRequest,
    PublishResult,
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
    publish_request = PublishRequest(
        source_dir=Path("extracted"),
        remote_url="https://gitlab.example.com/group/repo.git",
        branch="main",
        commit_message="Publish bundle",
    )
    publish_result = PublishResult(
        remote_url=publish_request.remote_url,
        branch=publish_request.branch,
        commit_sha="abc123",
        changed_file_count=1,
        pushed=True,
    )

    assert extraction.nested_bundle_path == Path("nested.tar.gz")
    assert filter_result.removed_paths == (Path("extracted/images/logo.png"),)
    assert chart_expansion_result.expanded_charts == (Path("extracted/frontend"),)
    assert publish_result.remote_url == publish_request.remote_url
