import logging
import shutil
import tempfile
from pathlib import Path
from typing import Any, Protocol, cast
from urllib.parse import quote, urlsplit, urlunsplit

from opentelemetry import (
    trace as trace_api,  # pyright: ignore[reportUnknownVariableType]
)

from sftp_watcher.bundle.models import (
    PreparedBundleRequest,
    PreparedBundleResult,
)
from sftp_watcher.config import GitPublisherConfig
from sftp_watcher.handler.git_command_runner import (
    GitCommandResult,
    GitCommandRunner,
)
from sftp_watcher.handler.git_publish_target import (
    GitPublishBranchResolver,
    GitPublishTargetResolver,
)

tracer: Any = cast(Any, trace_api).get_tracer(__name__)
logger = logging.getLogger(__name__)


class GitRunner(Protocol):
    def run(
        self,
        args: tuple[str, ...],
        *,
        cwd: Path | None = None,
    ) -> GitCommandResult: ...


class GitPreparedBundleHandler:
    PRESERVED_WORKTREE_PATHS = frozenset(
        {
            ".git",
            ".gitlab-ci.yml",
        }
    )

    def __init__(
        self,
        *,
        config: GitPublisherConfig,
        publish_target_resolver: GitPublishTargetResolver,
        publish_branch_resolver: GitPublishBranchResolver,
        git_runner: GitRunner | None = None,
    ) -> None:
        self._config = config
        self._publish_target_resolver = publish_target_resolver
        self._publish_branch_resolver = publish_branch_resolver
        self._git_runner = git_runner or GitCommandRunner(
            timeout_seconds=config.timeout_seconds,
            secrets=(config.password,) if config.password is not None else (),
        )

    def handle(self, request: PreparedBundleRequest) -> PreparedBundleResult:
        with tracer.start_as_current_span("sftp_watcher.git_handle_bundle") as span:
            metadata = {
                "tenant_id": request.tenant_id,
                "project_name": request.project_name,
                "project_version": request.project_version,
            }
            publish_target = self._publish_target_resolver.resolve(request.tenant_id)
            publish_branch = self._publish_branch_resolver.resolve(metadata)
            commit_message = f"Publish bundle {request.bundle_name}"

            span.set_attribute("tenant.id", request.tenant_id)
            span.set_attribute("project.name", request.project_name)
            span.set_attribute("project.version", request.project_version)
            span.set_attribute("git.remote_url", publish_target.remote_url)
            span.set_attribute("git.branch", publish_branch)

            logger.info(
                "Resolved Git publish target: tenant_id=%s project_name=%s "
                "project_version=%s remote_url=%s branch=%s",
                publish_target.tenant_id,
                request.project_name,
                request.project_version,
                publish_target.remote_url,
                publish_branch,
            )

            if not request.source_dir.exists():
                raise FileNotFoundError(
                    f"Publish source directory does not exist: {request.source_dir}"
                )

            if not request.source_dir.is_dir():
                raise ValueError(
                    f"Publish source path is not a directory: {request.source_dir}"
                )

            with tempfile.TemporaryDirectory() as temp_dir:
                repo_dir = Path(temp_dir) / "repository"
                clone_url = self._authenticated_remote_url(publish_target.remote_url)

                self._git_runner.run(
                    (
                        "clone",
                        "--branch",
                        self._config.branch,
                        "--single-branch",
                        clone_url,
                        "repository",
                    ),
                    cwd=repo_dir.parent,
                )

                self._checkout_publish_branch(
                    repo_dir=repo_dir,
                    branch=publish_branch,
                )

                self._replace_worktree_content(
                    source_dir=request.source_dir,
                    repo_dir=repo_dir,
                )

                status = self._git_runner.run(("status", "--porcelain"), cwd=repo_dir)
                changed_file_count = self._count_changed_files(status)
                span.set_attribute("git.changed_file_count", changed_file_count)

                if changed_file_count == 0:
                    span.set_attribute("git.pushed", False)
                    logger.info(
                        "No Git changes detected for prepared bundle: "
                        "remote_tarball_path=%s branch=%s",
                        request.remote_tarball_path,
                        publish_branch,
                    )
                    return PreparedBundleResult(
                        handled=False,
                        target=publish_target.remote_url,
                        branch=publish_branch,
                        commit_sha=None,
                        changed_file_count=0,
                    )

                self._git_runner.run(
                    ("config", "user.name", self._config.author_name),
                    cwd=repo_dir,
                )
                self._git_runner.run(
                    ("config", "user.email", self._config.author_email),
                    cwd=repo_dir,
                )
                self._git_runner.run(("add", "."), cwd=repo_dir)
                self._git_runner.run(("commit", "-m", commit_message), cwd=repo_dir)
                commit_sha = self._git_runner.run(("rev-parse", "HEAD"), cwd=repo_dir)
                self._git_runner.run(
                    ("push", "-u", "origin", publish_branch),
                    cwd=repo_dir,
                )

                span.set_attribute("git.pushed", True)
                span.set_attribute("git.commit_sha", commit_sha.stdout.strip())

                logger.info(
                    "Published bundle content to Git: remote_tarball_path=%s "
                    "branch=%s pushed=%s commit_sha=%s changed_file_count=%s",
                    request.remote_tarball_path,
                    publish_branch,
                    True,
                    commit_sha.stdout.strip(),
                    changed_file_count,
                )

                return PreparedBundleResult(
                    handled=True,
                    target=publish_target.remote_url,
                    branch=publish_branch,
                    commit_sha=commit_sha.stdout.strip(),
                    changed_file_count=changed_file_count,
                )

    def _checkout_publish_branch(self, *, repo_dir: Path, branch: str) -> None:
        if branch == self._config.branch:
            return

        remote_branch = self._git_runner.run(
            ("ls-remote", "--heads", "origin", branch),
            cwd=repo_dir,
        )

        if remote_branch.stdout.strip():
            self._git_runner.run(("fetch", "origin", branch), cwd=repo_dir)
            self._git_runner.run(
                ("checkout", "-B", branch, "FETCH_HEAD"),
                cwd=repo_dir,
            )
            return

        self._git_runner.run(("checkout", "-b", branch), cwd=repo_dir)

    def _authenticated_remote_url(self, remote_url: str) -> str:
        if self._config.username is None or self._config.password is None:
            return remote_url

        parsed_url = urlsplit(remote_url)

        if parsed_url.scheme not in {"http", "https"} or parsed_url.hostname is None:
            return remote_url

        username = quote(self._config.username, safe="")
        password = quote(self._config.password, safe="")
        port = f":{parsed_url.port}" if parsed_url.port is not None else ""
        netloc = f"{username}:{password}@{parsed_url.hostname}{port}"

        return urlunsplit(
            (
                parsed_url.scheme,
                netloc,
                parsed_url.path,
                parsed_url.query,
                parsed_url.fragment,
            )
        )

    def _replace_worktree_content(
        self,
        *,
        source_dir: Path,
        repo_dir: Path,
    ) -> None:
        for path in repo_dir.iterdir():
            if path.name in self.PRESERVED_WORKTREE_PATHS:
                continue

            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()

        for path in source_dir.iterdir():
            destination = repo_dir / path.name

            if path.is_dir():
                shutil.copytree(path, destination)
            else:
                shutil.copy2(path, destination)

    def _count_changed_files(self, status: GitCommandResult) -> int:
        return len([line for line in status.stdout.splitlines() if line.strip()])
