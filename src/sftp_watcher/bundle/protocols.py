from pathlib import Path
from typing import Protocol

from sftp_watcher.bundle.models import (
    BundleExtractionResult,
    BundleFilterResult,
    HelmChartExpansionResult,
    PreparedBundleRequest,
    PreparedBundleResult,
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


class PreparedBundleHandler(Protocol):
    def handle(self, request: PreparedBundleRequest) -> PreparedBundleResult: ...
