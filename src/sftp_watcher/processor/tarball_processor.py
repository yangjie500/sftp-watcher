import logging
import tempfile
from pathlib import Path
from typing import Any

from opentelemetry import trace
from opentelemetry.trace import Span

from sftp_watcher.processor.bundle_models import PublishRequest
from sftp_watcher.processor.bundle_protocols import (
    BundleContentFilter,
    BundleExtractor,
    HelmChartExpander,
    RepositoryPublisher,
)
from sftp_watcher.processor.git_publish_target import (
    GitPublishBranchResolver,
    GitPublishTargetResolver,
)
from sftp_watcher.processor.release_manifest_writer import ReleaseManifestWriter
from sftp_watcher.processor.tarball_metadata_extractor import (
    TarballMetadataExtractor,
)
from sftp_watcher.state_store.models import DownloadRecord
from sftp_watcher.utils import extract_filename_metadata

tracer = trace.get_tracer(__name__)
logger = logging.getLogger(__name__)


class TarballProcessor:
    GZIP_MAGIC = b"\x1f\x8b"
    TAR_MAGIC_OFFSET = 257
    TAR_MAGIC = b"ustar"
    FILENAME_METADATA_SEPARATOR = "-"
    TENANT_METADATA_NAME = "tenant_id"
    PROJECT_NAME_METADATA_NAME = "project_name"
    PROJECT_VERSION_METADATA_NAME = "project_version"
    FILENAME_METADATA_NAMES = (
        TENANT_METADATA_NAME,
        PROJECT_NAME_METADATA_NAME,
        PROJECT_VERSION_METADATA_NAME,
    )

    def __init__(
        self,
        *,
        bundle_extractor: BundleExtractor,
        content_filter: BundleContentFilter,
        helm_chart_expander: HelmChartExpander,
        repository_publisher: RepositoryPublisher,
        publish_target_resolver: GitPublishTargetResolver,
        publish_branch_resolver: GitPublishBranchResolver,
        release_manifest_writer: ReleaseManifestWriter | None = None,
        metadata_extractor: TarballMetadataExtractor | None = None,
    ) -> None:
        self._bundle_extractor = bundle_extractor
        self._content_filter = content_filter
        self._helm_chart_expander = helm_chart_expander
        self._repository_publisher = repository_publisher
        self._publish_target_resolver = publish_target_resolver
        self._publish_branch_resolver = publish_branch_resolver
        self._release_manifest_writer = (
            release_manifest_writer or ReleaseManifestWriter()
        )
        self._metadata_extractor = metadata_extractor or TarballMetadataExtractor()

    def can_process(self, record: DownloadRecord) -> bool:
        local_path = Path(record.local_path)

        if not local_path.exists() or not local_path.is_file():
            logger.debug(
                "Tarball processor skipped missing/non-file path: local_path=%s",
                local_path,
            )
            return False

        if self._looks_like_tar(local_path):
            logger.debug(
                "Tarball processor accepted file by tar magic: local_path=%s",
                local_path,
            )
            return True

        if self._looks_like_gzip(local_path):
            logger.debug(
                "Tarball processor accepted file by gzip magic: local_path=%s",
                local_path,
            )
            return True

        logger.debug(
            "Tarball processor skipped unsupported file: local_path=%s",
            local_path,
        )
        return False

    def process(self, record: DownloadRecord) -> None:
        with tracer.start_as_current_span("sftp_watcher.process_tarball") as span:
            span.set_attribute("sftp.remote_path", record.remote_path)
            span.set_attribute("sftp.local_path", record.local_path)
            span.set_attribute("sftp.file.size", record.size)
            span.set_attribute("sftp.file.mtime", record.mtime)

            local_path = Path(record.local_path)
            metadata: dict[str, Any] = {}

            try:
                metadata = self._metadata_extractor.extract(local_path)
            except Exception as error:
                span.record_exception(error)
                span.set_attribute("tarball.metadata.extracted", False)
                span.set_attribute("tarball.metadata.error", error.__class__.__name__)
                logger.warning(
                    "Failed to extract tarball metadata; continuing: "
                    "remote_path=%s local_path=%s",
                    record.remote_path,
                    local_path,
                    exc_info=True,
                )
            else:
                span.set_attribute("tarball.metadata.extracted", True)
                self._set_metadata_span_attributes(span, metadata)
                logger.info(
                    "Extracted tarball metadata: remote_path=%s local_path=%s "
                    "metadata=%s",
                    record.remote_path,
                    local_path,
                    metadata,
                )

            logger.info(
                "Processing tarball: remote_path=%s local_path=%s size=%s mtime=%s",
                record.remote_path,
                local_path,
                record.size,
                record.mtime,
            )

            filename_metadata = extract_filename_metadata(
                record.name,
                metadata_names=self.FILENAME_METADATA_NAMES,
                separator=self.FILENAME_METADATA_SEPARATOR,
            )
            tenant_id = filename_metadata[self.TENANT_METADATA_NAME]
            project_name = filename_metadata[self.PROJECT_NAME_METADATA_NAME]
            project_version = filename_metadata[self.PROJECT_VERSION_METADATA_NAME]
            publish_target = self._publish_target_resolver.resolve(tenant_id)
            publish_branch = self._publish_branch_resolver.resolve(filename_metadata)

            span.set_attribute("tenant.id", publish_target.tenant_id)
            span.set_attribute("project.name", project_name)
            span.set_attribute("project.version", project_version)
            span.set_attribute("git.remote_url", publish_target.remote_url)
            span.set_attribute("git.branch", publish_branch)

            logger.info(
                "Resolved Git publish target: remote_path=%s tenant_id=%s "
                "project_name=%s project_version=%s remote_url=%s branch=%s",
                record.remote_path,
                publish_target.tenant_id,
                project_name,
                project_version,
                publish_target.remote_url,
                publish_branch,
            )

            with tempfile.TemporaryDirectory() as temp_dir:
                work_dir = Path(temp_dir)
                extraction_result = self._bundle_extractor.extract(
                    local_path,
                    work_dir,
                )
                span.set_attribute(
                    "bundle.outer_path",
                    str(extraction_result.outer_bundle_path),
                )
                if extraction_result.nested_bundle_path is not None:
                    span.set_attribute(
                        "bundle.nested_path",
                        str(extraction_result.nested_bundle_path),
                    )
                span.set_attribute(
                    "bundle.extracted_dir",
                    str(extraction_result.extracted_dir),
                )
                logger.info(
                    "Extracted bundle: remote_path=%s outer_path=%s nested_path=%s "
                    "extracted_dir=%s",
                    record.remote_path,
                    extraction_result.outer_bundle_path,
                    extraction_result.nested_bundle_path,
                    extraction_result.extracted_dir,
                )

                filter_result = self._content_filter.filter(
                    extraction_result.extracted_dir,
                )
                span.set_attribute(
                    "bundle.container_images.removed_count",
                    len(filter_result.removed_paths),
                )
                logger.info(
                    "Removed container image artifacts: remote_path=%s "
                    "removed_count=%s",
                    record.remote_path,
                    len(filter_result.removed_paths),
                )

                chart_expansion_result = self._helm_chart_expander.expand(
                    extraction_result.extracted_dir,
                )
                span.set_attribute(
                    "helm_chart.expanded_count",
                    len(chart_expansion_result.expanded_charts),
                )
                span.set_attribute(
                    "helm_chart.removed_package_count",
                    len(chart_expansion_result.removed_packages),
                )
                logger.info(
                    "Expanded packaged Helm charts: remote_path=%s "
                    "expanded_count=%s removed_package_count=%s",
                    record.remote_path,
                    len(chart_expansion_result.expanded_charts),
                    len(chart_expansion_result.removed_packages),
                )

                release_manifest_path = self._release_manifest_writer.write(
                    directory=extraction_result.extracted_dir,
                    tenant_id=tenant_id,
                    project_name=project_name,
                    project_version=project_version,
                    remote_tarball_path=record.remote_path,
                )
                span.set_attribute("release_manifest.written", True)
                span.set_attribute(
                    "release_manifest.path",
                    str(release_manifest_path),
                )
                logger.info(
                    "Wrote release manifest: remote_path=%s manifest_path=%s",
                    record.remote_path,
                    release_manifest_path,
                )

                publish_result = self._repository_publisher.publish(
                    PublishRequest(
                        source_dir=extraction_result.extracted_dir,
                        remote_url=publish_target.remote_url,
                        branch=publish_branch,
                        commit_message=f"Publish bundle {record.name}",
                    )
                )

                span.set_attribute("git.remote_url", publish_result.remote_url)
                span.set_attribute("git.branch", publish_result.branch)
                span.set_attribute(
                    "git.changed_file_count",
                    publish_result.changed_file_count,
                )
                span.set_attribute("git.pushed", publish_result.pushed)

                if publish_result.commit_sha is not None:
                    span.set_attribute("git.commit_sha", publish_result.commit_sha)

                logger.info(
                    "Published bundle content to Git: remote_path=%s branch=%s "
                    "pushed=%s commit_sha=%s changed_file_count=%s",
                    record.remote_path,
                    publish_result.branch,
                    publish_result.pushed,
                    publish_result.commit_sha,
                    publish_result.changed_file_count,
                )

            logger.info(
                "Finished processing tarball: remote_path=%s local_path=%s",
                record.remote_path,
                local_path,
            )

    def _looks_like_gzip(self, path: Path) -> bool:
        with path.open("rb") as file:
            return file.read(2) == self.GZIP_MAGIC

    def _looks_like_tar(self, path: Path) -> bool:
        with path.open("rb") as file:
            file.seek(self.TAR_MAGIC_OFFSET)
            return file.read(len(self.TAR_MAGIC)) == self.TAR_MAGIC

    def _set_metadata_span_attributes(
        self,
        span: Span,
        metadata: dict[str, Any],
    ) -> None:
        span.set_attribute("tarball.metadata.size_of_file", metadata["SIZEOFFILE"])
        span.set_attribute("tarball.metadata.time_date", metadata["TIMEDATE"])
        span.set_attribute(
            "tarball.metadata.time_taken_seconds",
            metadata["TIME_TAKEN_SECONDS"],
        )
        span.set_attribute(
            "tarball.metadata.time_taken_minutes",
            metadata["TIME_TAKEN_MINUTES"],
        )
        span.set_attribute(
            "tarball.metadata.time_taken_hours",
            metadata["TIME_TAKEN_HOURS"],
        )
        span.set_attribute("tarball.metadata.size_kb", metadata["SIZE_KB"])
        span.set_attribute("tarball.metadata.size_mb", metadata["SIZE_MB"])
        span.set_attribute("tarball.metadata.size_gb", metadata["SIZE_GB"])
