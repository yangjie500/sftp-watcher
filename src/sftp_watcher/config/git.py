import os
from dataclasses import dataclass

from sftp_watcher.config.utils import json_dict


@dataclass(frozen=True)
class GitPublisherConfig:
    remote_url: str | None = None
    branch: str = "main"
    branch_template: str = "{project_name}/{project_version}"
    tenant_remote_urls: dict[str, str] | None = None
    username: str | None = None
    password: str | None = None
    author_name: str = "sftp-watcher"
    author_email: str = "sftp-watcher@example.com"
    timeout_seconds: int = 60

    @classmethod
    def from_env(cls) -> "GitPublisherConfig":
        remote_url = os.getenv("GIT_REMOTE_URL")
        tenant_remote_urls = json_dict("GIT_TENANT_REMOTE_URLS_JSON")

        if not remote_url and not tenant_remote_urls:
            raise ValueError(
                "Missing required environment variable: "
                "GIT_TENANT_REMOTE_URLS_JSON or GIT_REMOTE_URL"
            )

        return cls(
            remote_url=remote_url,
            branch=os.getenv("GIT_BRANCH", "main"),
            branch_template=os.getenv(
                "GIT_BRANCH_TEMPLATE",
                "{project_name}/{project_version}",
            ),
            tenant_remote_urls=tenant_remote_urls,
            username=os.getenv("GIT_USERNAME"),
            password=os.getenv("GIT_PASSWORD"),
            author_name=os.getenv("GIT_AUTHOR_NAME", "sftp-watcher"),
            author_email=os.getenv(
                "GIT_AUTHOR_EMAIL",
                "sftp-watcher@example.com",
            ),
            timeout_seconds=int(os.getenv("GIT_TIMEOUT_SECONDS", "60")),
        )
