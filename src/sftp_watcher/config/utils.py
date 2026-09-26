import json
import os
from pathlib import Path
from typing import Literal, Protocol, cast

from dotenv import (
    load_dotenv as _load_dotenv_untyped,  # type: ignore[reportUnknownVariableType]
)


# python-dotenv does not expose enough type information for Pyright strict mode.
# Keep the runtime function unchanged, but give Pyright the call shape we use.
class _LoadDotenv(Protocol):
    def __call__(self, dotenv_path: Path | None = None) -> bool: ...


load_dotenv = cast(_LoadDotenv, _load_dotenv_untyped)

CredentialSource = Literal["config", "cyberark_ccp"]
AAPAuthMethod = Literal["token", "basic"]


def load_environment(env_file: Path | None = None) -> None:
    if env_file:
        load_dotenv(env_file)
        return

    load_dotenv()


def required(name: str) -> str:
    value = os.getenv(name)

    if not value:
        raise ValueError(f"Missing required environment variable: {name}")

    return value


def csv_list(name: str) -> list[str] | None:
    value = os.getenv(name)

    if value is None or value.strip() == "":
        return None

    return [item.strip() for item in value.split(",") if item.strip()]


def csv_tuple(name: str, *, default: tuple[str, ...]) -> tuple[str, ...]:
    value = os.getenv(name)

    if value is None or value.strip() == "":
        return default

    return tuple(item.strip() for item in value.split(",") if item.strip())


def json_dict(name: str) -> dict[str, str] | None:
    value = os.getenv(name)

    if value is None or value.strip() == "":
        return None

    parsed = json.loads(value)

    if not isinstance(parsed, dict):
        raise ValueError(f"{name} must be a JSON object")

    # json.loads returns an untyped value to Pyright. After the runtime dict
    # check above, cast to object/object so the loop variables can be narrowed.
    parsed_mapping = cast("dict[object, object]", parsed)

    result: dict[str, str] = {}
    for key, item in parsed_mapping.items():
        if not isinstance(key, str) or not key:
            raise ValueError(f"{name} keys must be non-empty strings")

        if not isinstance(item, str) or not item:
            raise ValueError(f"{name} values must be non-empty strings")

        result[key] = item

    return result


def credential_source(value: str) -> CredentialSource:
    if value == "config":
        return "config"

    if value == "cyberark_ccp":
        return "cyberark_ccp"

    raise ValueError(
        "Invalid XXX_CREDENTIAL_SOURCE. Expected one of: config, cyberark_ccp"
    )


def aap_auth_method(value: str) -> AAPAuthMethod:
    if value == "token":
        return "token"

    if value == "basic":
        return "basic"

    raise ValueError("Invalid AAP_AUTH_METHOD. Expected one of: token, basic")


def bool_env(name: str, *, default: bool) -> bool:
    value = os.getenv(name)

    if value is None or value.strip() == "":
        return default

    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def optional_path(name: str) -> Path | None:
    value = os.getenv(name)

    if value is None or value.strip() == "":
        return None

    return Path(value)
