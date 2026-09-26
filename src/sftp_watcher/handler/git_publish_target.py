from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class GitPublishTarget:
    tenant_id: str
    remote_url: str
    branch: str


class GitPublishTargetResolver(Protocol):
    def resolve(self, tenant_id: str) -> GitPublishTarget: ...


class GitPublishBranchResolver(Protocol):
    def resolve(self, metadata: Mapping[str, str]) -> str: ...


class MappingGitPublishTargetResolver:
    def __init__(
        self,
        *,
        tenant_remote_urls: Mapping[str, str],
        default_branch: str,
        fallback_remote_url: str | None = None,
    ) -> None:
        self._tenant_remote_urls = dict(tenant_remote_urls)
        self._default_branch = default_branch
        self._fallback_remote_url = fallback_remote_url

    def resolve(self, tenant_id: str) -> GitPublishTarget:
        remote_url = self._tenant_remote_urls.get(tenant_id)

        if remote_url is None:
            remote_url = self._fallback_remote_url

        if remote_url is None:
            raise KeyError(f"No Git remote URL configured for tenant_id={tenant_id}")

        return GitPublishTarget(
            tenant_id=tenant_id,
            remote_url=remote_url,
            branch=self._default_branch,
        )


class TemplateGitPublishBranchResolver:
    def __init__(self, *, branch_template: str) -> None:
        self._branch_template = branch_template

    def resolve(self, metadata: Mapping[str, str]) -> str:
        try:
            branch = self._branch_template.format_map(dict(metadata)).strip()
        except KeyError as error:
            raise KeyError(
                f"Missing filename metadata required by branch template: {error}"
            ) from error

        self._validate_branch_name(branch)

        return branch

    def _validate_branch_name(self, branch: str) -> None:
        if not branch:
            raise ValueError("Git branch name cannot be empty")

        if branch == "@" or branch.startswith("-"):
            raise ValueError(f"Invalid Git branch name: {branch}")

        if branch.startswith("/") or branch.endswith("/") or branch.endswith("."):
            raise ValueError(f"Invalid Git branch name: {branch}")

        if ".." in branch or "//" in branch or "@{" in branch:
            raise ValueError(f"Invalid Git branch name: {branch}")

        invalid_chars = set(" ~^:?*[\\")
        if any(char in invalid_chars or ord(char) < 32 for char in branch):
            raise ValueError(f"Invalid Git branch name: {branch}")

        for component in branch.split("/"):
            if (
                not component
                or component.startswith(".")
                or component.endswith(".lock")
            ):
                raise ValueError(f"Invalid Git branch name: {branch}")
