import pytest

from sftp_watcher.config import BundleProcessingConfig, GitPublisherConfig


def test_git_publisher_config_reads_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GIT_REMOTE_URL", "https://gitlab.example.com/group/repo.git")
    monkeypatch.delenv("GIT_BRANCH", raising=False)
    monkeypatch.delenv("GIT_BRANCH_TEMPLATE", raising=False)
    monkeypatch.delenv("GIT_TENANT_REMOTE_URLS_JSON", raising=False)
    monkeypatch.delenv("GIT_USERNAME", raising=False)
    monkeypatch.delenv("GIT_PASSWORD", raising=False)
    monkeypatch.delenv("GIT_AUTHOR_NAME", raising=False)
    monkeypatch.delenv("GIT_AUTHOR_EMAIL", raising=False)
    monkeypatch.delenv("GIT_TIMEOUT_SECONDS", raising=False)

    config = GitPublisherConfig.from_env()

    assert config.remote_url == "https://gitlab.example.com/group/repo.git"
    assert config.branch == "main"
    assert config.branch_template == "{project_name}/{project_version}"
    assert config.tenant_remote_urls is None
    assert config.username is None
    assert config.password is None
    assert config.author_name == "sftp-watcher"
    assert config.author_email == "sftp-watcher@example.com"
    assert config.timeout_seconds == 60


def test_git_publisher_config_reads_custom_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GIT_REMOTE_URL", "https://gitlab.example.com/group/repo.git")
    monkeypatch.setenv("GIT_BRANCH", "release")
    monkeypatch.setenv(
        "GIT_BRANCH_TEMPLATE",
        "release/{project_name}-{project_version}",
    )
    monkeypatch.setenv(
        "GIT_TENANT_REMOTE_URLS_JSON",
        '{"tenant-a":"https://gitlab.example.com/group/tenant-a.git"}',
    )
    monkeypatch.setenv("GIT_USERNAME", "git-user")
    monkeypatch.setenv("GIT_PASSWORD", "git-password")
    monkeypatch.setenv("GIT_AUTHOR_NAME", "Release Bot")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "release-bot@example.com")
    monkeypatch.setenv("GIT_TIMEOUT_SECONDS", "120")

    config = GitPublisherConfig.from_env()

    assert config.remote_url == "https://gitlab.example.com/group/repo.git"
    assert config.branch == "release"
    assert config.branch_template == "release/{project_name}-{project_version}"
    assert config.tenant_remote_urls == {
        "tenant-a": "https://gitlab.example.com/group/tenant-a.git",
    }
    assert config.username == "git-user"
    assert config.password == "git-password"
    assert config.author_name == "Release Bot"
    assert config.author_email == "release-bot@example.com"
    assert config.timeout_seconds == 120


def test_git_publisher_config_requires_remote_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GIT_REMOTE_URL", raising=False)
    monkeypatch.delenv("GIT_TENANT_REMOTE_URLS_JSON", raising=False)

    with pytest.raises(
        ValueError,
        match="GIT_TENANT_REMOTE_URLS_JSON or GIT_REMOTE_URL",
    ):
        GitPublisherConfig.from_env()


def test_git_publisher_config_allows_tenant_remote_urls_without_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GIT_REMOTE_URL", raising=False)
    monkeypatch.setenv(
        "GIT_TENANT_REMOTE_URLS_JSON",
        '{"tenant-a":"https://gitlab.example.com/group/tenant-a.git"}',
    )

    config = GitPublisherConfig.from_env()

    assert config.remote_url is None
    assert config.tenant_remote_urls == {
        "tenant-a": "https://gitlab.example.com/group/tenant-a.git",
    }


def test_bundle_processing_config_reads_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("BUNDLE_FILENAME_METADATA_SEPARATOR", raising=False)
    monkeypatch.delenv("BUNDLE_CONTAINER_IMAGE_DIRS", raising=False)

    config = BundleProcessingConfig.from_env()

    assert config.filename_metadata_separator == "-+"
    assert config.container_image_dirs == (
        "images",
        "image",
        "container-images",
        "oci-images",
    )


def test_bundle_processing_config_reads_custom_dirs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BUNDLE_FILENAME_METADATA_SEPARATOR", "__")
    monkeypatch.setenv(
        "BUNDLE_CONTAINER_IMAGE_DIRS",
        "offline-images, image-archives ",
    )

    config = BundleProcessingConfig.from_env()

    assert config.filename_metadata_separator == "__"
    assert config.container_image_dirs == ("offline-images", "image-archives")


@pytest.mark.parametrize("separator", ["", "   "])
def test_bundle_processing_config_rejects_empty_separator(
    monkeypatch: pytest.MonkeyPatch,
    separator: str,
) -> None:
    monkeypatch.setenv("BUNDLE_FILENAME_METADATA_SEPARATOR", separator)

    with pytest.raises(
        ValueError,
        match="BUNDLE_FILENAME_METADATA_SEPARATOR must not be empty",
    ):
        BundleProcessingConfig.from_env()
