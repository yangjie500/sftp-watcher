import json
import tarfile
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class TarballMetadataExtractor:
    def extract(self, tarball_path: Path) -> dict[str, Any]:
        with tempfile.TemporaryDirectory() as temp_dir:
            extract_dir = Path(temp_dir)

            self._safe_extract_tarball(tarball_path, extract_dir)

            metadata_file = extract_dir / "TIMESTAMP.json"

            if not metadata_file.exists():
                raise FileNotFoundError(
                    f"Tarball {tarball_path.name} does not contain TIMESTAMP.json"
                )

            metadata = json.loads(metadata_file.read_text(encoding="utf-8"))

            required_keys = {"SIZEOFFILE", "TIMEDATE"}
            missing_keys = required_keys - metadata.keys()

            if missing_keys:
                raise ValueError(
                    f"TIMESTAMP.json missing required keys: {sorted(missing_keys)}"
                )

            size_str = str(metadata["SIZEOFFILE"])
            size_value_str, size_unit = size_str.split()

            size_kb = float(size_value_str)

            if size_unit.upper() != "KB":
                raise ValueError(f"Unsupported SIZEOFFILE unit: {size_unit}")

            timestamp_str = str(metadata["TIMEDATE"])

            try:
                timestamp = datetime.strptime(timestamp_str, "%Y%m%dT%H%M%S").replace(
                    tzinfo=UTC
                )
            except ValueError as error:
                raise ValueError(
                    f"Invalid TIMESTAMP format: {timestamp_str}"
                ) from error

            time_taken_seconds = (datetime.now(UTC) - timestamp).total_seconds()

            return {
                "tarball_name": tarball_path.name,
                "SIZEOFFILE": size_str,
                "TIMEDATE": timestamp_str,
                "TIME_TAKEN_SECONDS": int(time_taken_seconds),
                "TIME_TAKEN_MINUTES": round(time_taken_seconds / 60, 2),
                "TIME_TAKEN_HOURS": round(time_taken_seconds / 3600, 2),
                "SIZE_KB": round(size_kb, 2),
                "SIZE_MB": round(size_kb / 1024, 2),
                "SIZE_GB": round(size_kb / 1024 / 1024, 4),
            }

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
