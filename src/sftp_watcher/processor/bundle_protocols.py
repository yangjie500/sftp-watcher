from pathlib import Path
from typing import Protocol

from sftp_watcher.processor.bundle_models import (
    BundleExtractionResult,
    BundleFilterResult,
    HelmChartExpansionResult,
    PublishRequest,
    PublishResult,
)


class BundleExtractor(Protocol):
    def extract(
        self,
        bundle_path: Path,
        destination_dir: Path,
    ) -> BundleExtractionResult: ...


class BundleContentFilter(Protocol):
    def filter(self, directory: Path) -> BundleFilterResult: ...


class HelmChartExpander(Protocol):
    def expand(self, directory: Path) -> HelmChartExpansionResult: ...


class RepositoryPublisher(Protocol):
    def publish(self, request: PublishRequest) -> PublishResult: ...
