import pytest

from sftp_watcher.utils import extract_filename_metadata


def test_extract_filename_metadata_maps_values_by_name_order() -> None:
    metadata = extract_filename_metadata(
        "customer-+environment-+version.tar.gz.bundle",
        metadata_names=["customer", "environment", "version"],
        separator="-+",
    )

    assert metadata == {
        "customer": "customer",
        "environment": "environment",
        "version": "version",
    }


def test_extract_filename_metadata_uses_basename() -> None:
    metadata = extract_filename_metadata(
        "/remote/incoming/customer-+environment-+version.tar.gz.bundle",
        metadata_names=["customer", "environment", "version"],
        separator="-+",
    )

    assert metadata == {
        "customer": "customer",
        "environment": "environment",
        "version": "version",
    }


def test_extract_filename_metadata_extracts_requested_prefix_only() -> None:
    metadata = extract_filename_metadata(
        "customer-+environment-+version.tar.gz.bundle",
        metadata_names=["customer", "environment"],
        separator="-+",
    )

    assert metadata == {
        "customer": "customer",
        "environment": "environment",
    }


def test_extract_filename_metadata_rejects_wrong_suffix() -> None:
    with pytest.raises(ValueError, match="Filename must end with"):
        extract_filename_metadata(
            "customer-+environment-+version.tar.gz",
            metadata_names=["customer", "environment", "version"],
            separator="-+",
        )


def test_extract_filename_metadata_rejects_too_many_metadata_names() -> None:
    with pytest.raises(ValueError, match="fewer metadata values than requested"):
        extract_filename_metadata(
            "customer-+environment.tar.gz.bundle",
            metadata_names=["customer", "environment", "version"],
            separator="-+",
        )


def test_extract_filename_metadata_rejects_duplicate_metadata_names() -> None:
    with pytest.raises(ValueError, match="duplicate names"):
        extract_filename_metadata(
            "customer-+environment-+version.tar.gz.bundle",
            metadata_names=["customer", "customer"],
            separator="-+",
        )
