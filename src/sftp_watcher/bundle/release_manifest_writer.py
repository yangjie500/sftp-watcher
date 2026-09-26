import json
from pathlib import Path


class ReleaseManifestWriter:
    MANIFEST_FILENAME = "release.json"

    def write(
        self,
        *,
        directory: Path,
        tenant_id: str,
        project_name: str,
        project_version: str,
        remote_tarball_path: str,
    ) -> Path:
        if not directory.exists():
            raise FileNotFoundError(
                f"Release manifest directory does not exist: {directory}"
            )

        if not directory.is_dir():
            raise ValueError(f"Release manifest path is not a directory: {directory}")

        manifest_path = directory / self.MANIFEST_FILENAME
        manifest = {
            "tenant_id": tenant_id,
            "project_name": project_name,
            "project_version": project_version,
            "remote_tarball_path": remote_tarball_path,
        }

        manifest_path.write_text(
            json.dumps(manifest, indent=2) + "\n",
            encoding="utf-8",
        )

        return manifest_path
