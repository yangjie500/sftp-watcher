from pathlib import Path
from typing import Any

import pytest

from sftp_watcher.processor.bundle_models import (
    BundleExtractionResult,
    BundleFilterResult,
    HelmChartExpansionResult,
    PublishRequest,
    PublishResult,
)
from sftp_watcher.processor.git_publish_target import (
    MappingGitPublishTargetResolver,
    TemplateGitPublishBranchResolver,
)
from sftp_watcher.processor.release_manifest_writer import ReleaseManifestWriter
from sftp_watcher.processor.tarball_metadata_extractor import TarballMetadataExtractor
from sftp_watcher.processor.tarball_processor import TarballProcessor
from sftp_watcher.state_store.models import DownloadRecord


def test_process_extracts_filters_and_publishes_bundle(tmp_path: Path) -> None:
    local_path = tmp_path / "tenant-a-+my-project-+1.2.3-+20241028T115959.tar.gz.bundle"
    local_path.write_bytes(b"bundle")
    bundle_extractor = FakeBundleExtractor()
    content_filter = FakeContentFilter()
    helm_chart_expander = FakeHelmChartExpander()
    repository_publisher = FakeRepositoryPublisher()
    release_manifest_writer = FakeReleaseManifestWriter()

    TarballProcessor(
        bundle_extractor=bundle_extractor,
        content_filter=content_filter,
        helm_chart_expander=helm_chart_expander,
        repository_publisher=repository_publisher,
        publish_target_resolver=_publish_target_resolver(),
        publish_branch_resolver=_publish_branch_resolver(),
        release_manifest_writer=release_manifest_writer,
        metadata_extractor=FakeMetadataExtractor(),
    ).process(_record(local_path))

    assert bundle_extractor.bundle_path == local_path
    assert bundle_extractor.destination_dir is not None
    assert content_filter.directory == bundle_extractor.extracted_dir
    assert helm_chart_expander.directory == bundle_extractor.extracted_dir
    assert release_manifest_writer.request == {
        "directory": bundle_extractor.extracted_dir,
        "tenant_id": "tenant-a",
        "project_name": "my-project",
        "project_version": "1.2.3",
        "remote_tarball_path": (
            "/remote/tenant-a-+my-project-+1.2.3-+20241028T115959.tar.gz.bundle"
        ),
    }
    assert repository_publisher.request == PublishRequest(
        source_dir=bundle_extractor.extracted_dir,
        remote_url="https://gitlab.example.com/group/tenant-a.git",
        branch="my-project/1.2.3",
        commit_message=(
            "Publish bundle tenant-a-+my-project-+1.2.3-+20241028T115959.tar.gz.bundle"
        ),
    )


def test_process_continues_when_metadata_extraction_fails(tmp_path: Path) -> None:
    local_path = tmp_path / "tenant-a-+my-project-+1.2.3.tar.gz.bundle"
    local_path.write_bytes(b"bundle")
    bundle_extractor = FakeBundleExtractor()
    content_filter = FakeContentFilter()
    repository_publisher = FakeRepositoryPublisher()

    TarballProcessor(
        bundle_extractor=bundle_extractor,
        content_filter=content_filter,
        helm_chart_expander=FakeHelmChartExpander(),
        repository_publisher=repository_publisher,
        publish_target_resolver=_publish_target_resolver(),
        publish_branch_resolver=_publish_branch_resolver(),
        release_manifest_writer=FakeReleaseManifestWriter(),
        metadata_extractor=FakeMetadataExtractor(error=ValueError("bad metadata")),
    ).process(_record(local_path))

    assert bundle_extractor.bundle_path == local_path
    assert content_filter.directory == bundle_extractor.extracted_dir
    assert repository_publisher.request is not None


def test_process_uses_configured_filename_metadata_separator(tmp_path: Path) -> None:
    local_path = tmp_path / "tenant-a__my-project__1.2.3.tar.gz.bundle"
    local_path.write_bytes(b"bundle")
    bundle_extractor = FakeBundleExtractor()
    repository_publisher = FakeRepositoryPublisher()
    release_manifest_writer = FakeReleaseManifestWriter()

    TarballProcessor(
        bundle_extractor=bundle_extractor,
        content_filter=FakeContentFilter(),
        helm_chart_expander=FakeHelmChartExpander(),
        repository_publisher=repository_publisher,
        publish_target_resolver=_publish_target_resolver(),
        publish_branch_resolver=_publish_branch_resolver(),
        release_manifest_writer=release_manifest_writer,
        metadata_extractor=FakeMetadataExtractor(),
        filename_metadata_separator="__",
    ).process(_record(local_path))

    assert release_manifest_writer.request == {
        "directory": bundle_extractor.extracted_dir,
        "tenant_id": "tenant-a",
        "project_name": "my-project",
        "project_version": "1.2.3",
        "remote_tarball_path": "/remote/tenant-a__my-project__1.2.3.tar.gz.bundle",
    }
    assert repository_publisher.request is not None
    assert repository_publisher.request.remote_url == (
        "https://gitlab.example.com/group/tenant-a.git"
    )
    assert repository_publisher.request.branch == "my-project/1.2.3"


def test_process_bubbles_publish_error(tmp_path: Path) -> None:
    local_path = tmp_path / "tenant-a-+my-project-+1.2.3.tar.gz.bundle"
    local_path.write_bytes(b"bundle")

    processor = TarballProcessor(
        bundle_extractor=FakeBundleExtractor(),
        content_filter=FakeContentFilter(),
        helm_chart_expander=FakeHelmChartExpander(),
        repository_publisher=FakeRepositoryPublisher(
            error=RuntimeError("git push failed")
        ),
        publish_target_resolver=_publish_target_resolver(),
        publish_branch_resolver=_publish_branch_resolver(),
        release_manifest_writer=FakeReleaseManifestWriter(),
        metadata_extractor=FakeMetadataExtractor(),
    )

    with pytest.raises(RuntimeError, match="git push failed"):
        processor.process(_record(local_path))


def test_process_bubbles_unknown_tenant_error(tmp_path: Path) -> None:
    local_path = tmp_path / "tenant-b-+my-project-+1.2.3.tar.gz.bundle"
    local_path.write_bytes(b"bundle")

    processor = TarballProcessor(
        bundle_extractor=FakeBundleExtractor(),
        content_filter=FakeContentFilter(),
        helm_chart_expander=FakeHelmChartExpander(),
        repository_publisher=FakeRepositoryPublisher(),
        publish_target_resolver=_publish_target_resolver(),
        publish_branch_resolver=_publish_branch_resolver(),
        release_manifest_writer=FakeReleaseManifestWriter(),
        metadata_extractor=FakeMetadataExtractor(),
    )

    with pytest.raises(KeyError, match="tenant-b"):
        processor.process(_record(local_path))


class FakeBundleExtractor:
    def __init__(self) -> None:
        self.bundle_path: Path | None = None
        self.destination_dir: Path | None = None
        self.extracted_dir = Path()

    def extract(
        self,
        bundle_path: Path,
        destination_dir: Path,
    ) -> BundleExtractionResult:
        self.bundle_path = bundle_path
        self.destination_dir = destination_dir
        self.extracted_dir = destination_dir / "extracted"
        self.extracted_dir.mkdir()

        return BundleExtractionResult(
            outer_bundle_path=bundle_path,
            nested_bundle_path=destination_dir / "outer/payload/release.tar.gz",
            extracted_dir=self.extracted_dir,
        )


class FakeContentFilter:
    def __init__(self) -> None:
        self.directory: Path | None = None

    def filter(self, directory: Path) -> BundleFilterResult:
        self.directory = directory

        return BundleFilterResult(
            removed_paths=(directory / "images/app.tar",),
            remaining_paths=(directory / "charts/app/Chart.yaml",),
        )


class FakeHelmChartExpander:
    def __init__(self) -> None:
        self.directory: Path | None = None

    def expand(self, directory: Path) -> HelmChartExpansionResult:
        self.directory = directory

        return HelmChartExpansionResult(
            expanded_charts=(directory / "frontend",),
            removed_packages=(directory / "frontend-1.2.3.tgz",),
        )


class FakeRepositoryPublisher:
    def __init__(self, *, error: Exception | None = None) -> None:
        self._error = error
        self.request: PublishRequest | None = None

    def publish(self, request: PublishRequest) -> PublishResult:
        self.request = request

        if self._error is not None:
            raise self._error

        return PublishResult(
            remote_url=request.remote_url,
            branch=request.branch,
            commit_sha="abc123",
            changed_file_count=1,
            pushed=True,
        )


class FakeReleaseManifestWriter(ReleaseManifestWriter):
    def __init__(self) -> None:
        self.request: dict[str, object] | None = None

    def write(
        self,
        *,
        directory: Path,
        tenant_id: str,
        project_name: str,
        project_version: str,
        remote_tarball_path: str,
    ) -> Path:
        self.request = {
            "directory": directory,
            "tenant_id": tenant_id,
            "project_name": project_name,
            "project_version": project_version,
            "remote_tarball_path": remote_tarball_path,
        }

        return directory / "release.json"


class FakeMetadataExtractor(TarballMetadataExtractor):
    def __init__(self, *, error: Exception | None = None) -> None:
        self._error = error

    def extract(self, tarball_path: Path) -> dict[str, Any]:
        if self._error is not None:
            raise self._error

        return {
            "SIZEOFFILE": "2048 KB",
            "TIMEDATE": "20241028T115959",
            "TIME_TAKEN_SECONDS": 60,
            "TIME_TAKEN_MINUTES": 1.0,
            "TIME_TAKEN_HOURS": 0.02,
            "SIZE_KB": 2048.0,
            "SIZE_MB": 2.0,
            "SIZE_GB": 0.002,
        }


def _record(local_path: Path) -> DownloadRecord:
    return DownloadRecord(
        name=local_path.name,
        remote_path=f"/remote/{local_path.name}",
        local_path=str(local_path),
        size=123,
        mtime=456,
    )


def _publish_target_resolver() -> MappingGitPublishTargetResolver:
    return MappingGitPublishTargetResolver(
        tenant_remote_urls={
            "tenant-a": "https://gitlab.example.com/group/tenant-a.git",
        },
        default_branch="main",
    )


def _publish_branch_resolver() -> TemplateGitPublishBranchResolver:
    return TemplateGitPublishBranchResolver(
        branch_template="{project_name}/{project_version}",
    )
