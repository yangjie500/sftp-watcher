import shutil
from collections.abc import Sequence
from pathlib import Path

from sftp_watcher.bundle.models import BundleFilterResult


class ContainerImageRemovingBundleContentFilter:
    CONTAINER_IMAGE_DIRS = (
        "images",
        "image",
        "container-images",
        "oci-images",
    )

    def __init__(
        self,
        *,
        container_image_dirs: Sequence[str] = CONTAINER_IMAGE_DIRS,
    ) -> None:
        self._container_image_dir_order = {
            directory.lower(): index
            for index, directory in enumerate(container_image_dirs)
        }
        self._container_image_dirs = frozenset(self._container_image_dir_order)

    def filter(self, directory: Path) -> BundleFilterResult:
        if not directory.exists():
            raise FileNotFoundError(
                f"Bundle content directory does not exist: {directory}"
            )

        if not directory.is_dir():
            raise ValueError(f"Bundle content path is not a directory: {directory}")

        removed_paths: list[Path] = []

        # Filesystems do not guarantee traversal order. Sort by configured image
        # directory order so removed_paths is stable locally and in CI.
        paths = sorted(
            directory.rglob("*"),
            key=lambda item: (
                len(item.parts),
                self._container_image_dir_order.get(item.name.lower(), len(item.parts)),
                item.as_posix(),
            ),
        )

        for path in paths:
            if not path.is_dir():
                continue

            if path.name.lower() not in self._container_image_dirs:
                continue

            removed_paths.extend(
                child for child in sorted(path.rglob("*")) if child.is_file()
            )
            removed_paths.append(path)
            shutil.rmtree(path)

        remaining_paths = tuple(
            path for path in sorted(directory.rglob("*")) if path.is_file()
        )

        return BundleFilterResult(
            removed_paths=tuple(removed_paths),
            remaining_paths=remaining_paths,
        )
