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
class PreparedBundleRequest:
    source_dir: Path
    tenant_id: str
    project_name: str
    project_version: str
    remote_tarball_path: str
    bundle_name: str


@dataclass(frozen=True)
class PreparedBundleResult:
    handled: bool
    changed_file_count: int
    target: str | None = None
    branch: str | None = None
    commit_sha: str | None = None
