from collections.abc import Sequence
from pathlib import PurePath


def extract_filename_metadata(
    filename: str,
    *,
    metadata_names: Sequence[str],
    separator: str,
    suffix: str = ".tar.gz.bundle",
) -> dict[str, str]:
    """Extract ordered metadata values from a bundle filename."""
    names = list(metadata_names)

    if any(name == "" for name in names):
        raise ValueError("metadata_names cannot contain empty names")

    if len(names) != len(set(names)):
        raise ValueError("metadata_names cannot contain duplicate names")

    name = PurePath(filename).name
    if suffix and not name.endswith(suffix):
        raise ValueError(f"Filename must end with {suffix!r}: {filename!r}")

    metadata_part = name.removesuffix(suffix) if suffix else name
    values = metadata_part.split(separator)

    if len(names) > len(values):
        raise ValueError(
            "Filename provides fewer metadata values than requested: "
            f"requested_count={len(names)} actual_count={len(values)} "
            f"filename={filename!r}"
        )

    if any(value == "" for value in values):
        raise ValueError(f"Filename contains empty metadata value: {filename!r}")

    return dict(zip(names, values[: len(names)], strict=True))
