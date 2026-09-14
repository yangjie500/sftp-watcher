import pytest

from sftp_watcher.processor.git_publish_target import (
    GitPublishTarget,
    MappingGitPublishTargetResolver,
    TemplateGitPublishBranchResolver,
)


def test_mapping_git_publish_target_resolver_returns_tenant_url() -> None:
    resolver = MappingGitPublishTargetResolver(
        tenant_remote_urls={
            "tenant-a": "https://gitlab.example.com/group/tenant-a.git",
        },
        default_branch="main",
        fallback_remote_url="https://gitlab.example.com/group/default.git",
    )

    assert resolver.resolve("tenant-a") == GitPublishTarget(
        tenant_id="tenant-a",
        remote_url="https://gitlab.example.com/group/tenant-a.git",
        branch="main",
    )


def test_mapping_git_publish_target_resolver_uses_fallback_url() -> None:
    resolver = MappingGitPublishTargetResolver(
        tenant_remote_urls={},
        default_branch="main",
        fallback_remote_url="https://gitlab.example.com/group/default.git",
    )

    assert resolver.resolve("tenant-a") == GitPublishTarget(
        tenant_id="tenant-a",
        remote_url="https://gitlab.example.com/group/default.git",
        branch="main",
    )


def test_mapping_git_publish_target_resolver_rejects_unknown_tenant() -> None:
    resolver = MappingGitPublishTargetResolver(
        tenant_remote_urls={},
        default_branch="main",
    )

    with pytest.raises(KeyError, match="tenant-a"):
        resolver.resolve("tenant-a")


def test_template_git_publish_branch_resolver_formats_branch() -> None:
    resolver = TemplateGitPublishBranchResolver(
        branch_template="{project_name}/{project_version}",
    )

    assert (
        resolver.resolve(
            {
                "project_name": "my-project",
                "project_version": "1.2.3",
            }
        )
        == "my-project/1.2.3"
    )


def test_template_git_publish_branch_resolver_rejects_missing_metadata() -> None:
    resolver = TemplateGitPublishBranchResolver(
        branch_template="{project_name}/{project_version}",
    )

    with pytest.raises(KeyError, match="project_version"):
        resolver.resolve({"project_name": "my-project"})


def test_template_git_publish_branch_resolver_rejects_invalid_branch() -> None:
    resolver = TemplateGitPublishBranchResolver(
        branch_template="{project_name}/{project_version}",
    )

    with pytest.raises(ValueError, match="Invalid Git branch name"):
        resolver.resolve(
            {
                "project_name": "my project",
                "project_version": "1.2.3",
            }
        )
