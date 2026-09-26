import tarfile
from collections.abc import Sequence
from pathlib import Path

from sftp_watcher.bundle.models import BundleExtractionResult


class SafeTarBundleExtractor:
    TAR_SUFFIXES = (
        ".tar",
        ".tar.gz",
        ".tgz",
        ".tar.bz2",
        ".tbz2",
        ".tar.xz",
        ".txz",
    )
    SIGNATURE_SUFFIXES = (".sig", ".signature", ".asc")

    def __init__(
        self,
        *,
        tar_suffixes: Sequence[str] = TAR_SUFFIXES,
        signature_suffixes: Sequence[str] = SIGNATURE_SUFFIXES,
    ) -> None:
        self._tar_suffixes = tuple(tar_suffixes)
        self._signature_suffixes = tuple(signature_suffixes)

    def extract(
        self,
        bundle_path: Path,
        destination_dir: Path,
    ) -> BundleExtractionResult:
        outer_extract_dir = destination_dir / "outer"
        nested_extract_dir = destination_dir / "extracted"

        outer_extract_dir.mkdir(parents=True, exist_ok=True)
        nested_extract_dir.mkdir(parents=True, exist_ok=True)

        self._safe_extract_tarball(bundle_path, outer_extract_dir)

        nested_bundle_path = self._find_nested_bundle(outer_extract_dir)

        self._safe_extract_tarball(nested_bundle_path, nested_extract_dir)

        return BundleExtractionResult(
            outer_bundle_path=bundle_path,
            nested_bundle_path=nested_bundle_path,
            extracted_dir=nested_extract_dir,
        )

    def _find_nested_bundle(self, outer_extract_dir: Path) -> Path:
        signature_paths = self._find_signature_paths(outer_extract_dir)

        if signature_paths:
            signature_dirs = {
                signature_path.parent for signature_path in signature_paths
            }
            candidates = self._find_tarball_candidates_in_dirs(signature_dirs)

            return self._select_single_candidate(
                candidates,
                empty_message="Could not find nested tarball next to signature file",
            )

        candidates = self._find_tarball_candidates(outer_extract_dir)

        return self._select_single_candidate(
            candidates,
            empty_message="Could not find nested tarball in unsigned outer bundle",
        )

    def _find_signature_paths(self, outer_extract_dir: Path) -> tuple[Path, ...]:
        return tuple(
            path
            for path in outer_extract_dir.rglob("*")
            if path.is_file()
            and self._has_supported_suffix(path, self._signature_suffixes)
        )

    def _find_tarball_candidates(self, directory: Path) -> list[Path]:
        return [
            path
            for path in directory.rglob("*")
            if path.is_file() and self._has_supported_suffix(path, self._tar_suffixes)
        ]

    def _find_tarball_candidates_in_dirs(self, directories: set[Path]) -> list[Path]:
        return [
            path
            for directory in directories
            for path in directory.iterdir()
            if path.is_file() and self._has_supported_suffix(path, self._tar_suffixes)
        ]

    def _select_single_candidate(
        self,
        candidates: list[Path],
        *,
        empty_message: str,
    ) -> Path:
        if not candidates:
            raise FileNotFoundError(empty_message)

        if len(candidates) > 1:
            candidate_names = sorted(str(candidate) for candidate in candidates)
            raise ValueError(
                f"Found multiple nested tarball candidates: {candidate_names}"
            )

        return candidates[0]

    def _safe_extract_tarball(self, tarball_path: Path, extract_dir: Path) -> None:
        with tarfile.open(tarball_path, mode="r:*") as tar:
            for member in tar.getmembers():
                target_path = extract_dir / member.name

                if not self._is_safe_path(extract_dir, target_path):
                    raise ValueError(f"Unsafe path detected in tarball: {member.name}")

            tar.extractall(extract_dir, filter="data")

    def _is_safe_path(self, base_dir: Path, target_path: Path) -> bool:
        base_dir = base_dir.resolve()
        target_path = target_path.resolve()

        return base_dir == target_path or base_dir in target_path.parents

    def _has_supported_suffix(self, path: Path, suffixes: Sequence[str]) -> bool:
        name = path.name.lower()

        return any(name.endswith(suffix.lower()) for suffix in suffixes)
