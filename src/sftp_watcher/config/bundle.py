import os
from dataclasses import dataclass

from sftp_watcher.config.utils import csv_tuple


@dataclass(frozen=True)
class BundleProcessingConfig:
    filename_metadata_separator: str = "-+"
    container_image_dirs: tuple[str, ...] = (
        "images",
        "image",
        "container-images",
        "oci-images",
    )

    @classmethod
    def from_env(cls) -> "BundleProcessingConfig":
        filename_metadata_separator = os.getenv(
            "BUNDLE_FILENAME_METADATA_SEPARATOR",
            cls.filename_metadata_separator,
        )
        _validate_filename_metadata_separator(filename_metadata_separator)

        return cls(
            filename_metadata_separator=filename_metadata_separator,
            container_image_dirs=csv_tuple(
                "BUNDLE_CONTAINER_IMAGE_DIRS",
                default=cls.container_image_dirs,
            ),
        )


def _validate_filename_metadata_separator(separator: str) -> None:
    if separator.strip() == "":
        raise ValueError("BUNDLE_FILENAME_METADATA_SEPARATOR must not be empty")
