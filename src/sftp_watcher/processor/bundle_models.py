from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BundleExtractionResult:
    outer_bundle_path: Path
    nested_bundle_path: Path | None
    extracted_dir: Path


@dataclass(frozen=True)
class BundleFilterResult:
    removed_paths: tuple[Path, ...]
    remaining_paths: tuple[Path, ...]


@dataclass(frozen=True)
class HelmChartExpansionResult:
    expanded_charts: tuple[Path, ...]
    removed_packages: tuple[Path, ...]


@dataclass(frozen=True)
class PublishRequest:
    source_dir: Path
    remote_url: str
    branch: str
    commit_message: str


@dataclass(frozen=True)
class PublishResult:
    remote_url: str
    branch: str
    commit_sha: str | None
    changed_file_count: int
    pushed: bool
