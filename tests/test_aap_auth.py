from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from sftp_watcher.config import AAPConfig
from sftp_watcher.processor.action.aap_client import AAPClient


def test_aap_config_defaults_to_token_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AAP_BASE_URL", "https://aap.example.com")
    monkeypatch.setenv("AAP_JOB_TEMPLATE_ID", "9")
    monkeypatch.setenv("AAP_TOKEN", "test-token")
    monkeypatch.delenv("AAP_AUTH_METHOD", raising=False)

    config = AAPConfig.from_env(Path("missing.env"))

    assert config.auth_method == "token"
    assert config.token == "test-token"


def test_aap_config_reads_basic_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AAP_BASE_URL", "https://aap.example.com")
    monkeypatch.setenv("AAP_JOB_TEMPLATE_ID", "9")
    monkeypatch.setenv("AAP_AUTH_METHOD", "basic")
    monkeypatch.setenv("AAP_USERNAME", "test-user")
    monkeypatch.setenv("AAP_PASSWORD", "test-password")
    monkeypatch.delenv("AAP_TOKEN", raising=False)

    config = AAPConfig.from_env(Path("missing.env"))

    assert config.auth_method == "basic"
    assert config.username == "test-user"
    assert config.password == "test-password"


def test_aap_config_requires_basic_password(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AAP_BASE_URL", "https://aap.example.com")
    monkeypatch.setenv("AAP_JOB_TEMPLATE_ID", "9")
    monkeypatch.setenv("AAP_AUTH_METHOD", "basic")
    monkeypatch.setenv("AAP_USERNAME", "test-user")
    monkeypatch.delenv("AAP_PASSWORD", raising=False)
    monkeypatch.delenv("AAP_TOKEN", raising=False)

    with pytest.raises(ValueError, match="AAP_PASSWORD"):
        AAPConfig.from_env(Path("missing.env"))


def test_aap_client_uses_token_auth_header() -> None:
    response = _successful_launch_response()
    config = AAPConfig(
        base_url="https://aap.example.com",
        token="test-token",
        job_template_id=9,
    )

    with patch("sftp_watcher.processor.action.aap_client.requests.post") as post:
        post.return_value = response

        job_id = AAPClient(config).launch_job_template(extra_vars={"key": "value"})

    assert job_id == 42
    post.assert_called_once()
    request_kwargs = post.call_args.kwargs
    assert request_kwargs["headers"]["Authorization"] == "Bearer test-token"
    assert request_kwargs["auth"] is None


def test_aap_client_uses_basic_auth_tuple() -> None:
    response = _successful_launch_response()
    config = AAPConfig(
        base_url="https://aap.example.com",
        token=None,
        job_template_id=9,
        auth_method="basic",
        username="test-user",
        password="test-password",
    )

    with patch("sftp_watcher.processor.action.aap_client.requests.post") as post:
        post.return_value = response

        job_id = AAPClient(config).launch_job_template(extra_vars={"key": "value"})

    assert job_id == 42
    post.assert_called_once()
    request_kwargs = post.call_args.kwargs
    assert "Authorization" not in request_kwargs["headers"]
    assert request_kwargs["auth"] == ("test-user", "test-password")


def _successful_launch_response() -> Mock:
    response = Mock()
    response.status_code = 201
    response.raise_for_status.return_value = None
    response.json.return_value = {"job": 42}
    return response
