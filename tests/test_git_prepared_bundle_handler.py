from pathlib import Path

import pytest

from sftp_watcher.bundle.models import PreparedBundleRequest
from sftp_watcher.config import GitPublisherConfig
from sftp_watcher.handler.git_command_runner import GitCommandResult
from sftp_watcher.handler.git_prepared_bundle_handler import (
    GitPreparedBundleHandler,
)
from sftp_watcher.handler.git_publish_target import (
    MappingGitPublishTargetResolver,
    TemplateGitPublishBranchResolver,
)


def test_handle_clones_commits_and_pushes_changed_content(tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    _write_file(source_dir / "charts/app/Chart.yaml", "apiVersion: v2\n")
    _write_file(source_dir / "metadata/release.json", "{}\n")
    git_runner = FakeGitRunner(status_stdout="A  charts/app/Chart.yaml\n")
    publisher = _publisher(
        config=GitPublisherConfig(
            remote_url="https://gitlab.example.com/group/repo.git",
            username="git-user",
            password="git-password",
            author_name="Release Bot",
            author_email="release-bot@example.com",
        ),
        git_runner=git_runner,
    )

    result = publisher.handle(_request(source_dir, bundle_name="bundle.tar.gz"))

    assert result.handled is True
    assert result.changed_file_count == 1
    assert result.commit_sha == "abc123"
    assert result.target == "https://gitlab.example.com/group/repo.git"
    assert git_runner.commands == (
        (
            "clone",
            "--branch",
            "main",
            "--single-branch",
            git_runner.clone_url,
            "repository",
        ),
        ("ls-remote", "--heads", "origin", "my-project/1.2.3"),
        ("checkout", "-b", "my-project/1.2.3"),
        ("status", "--porcelain"),
        ("config", "user.name", "Release Bot"),
        ("config", "user.email", "release-bot@example.com"),
        ("add", "."),
        ("commit", "-m", "Publish bundle bundle.tar.gz"),
        ("rev-parse", "HEAD"),
        ("push", "-u", "origin", "my-project/1.2.3"),
    )
    assert git_runner.clone_url == (
        "https://git-user:git-password@gitlab.example.com/group/repo.git"
    )
    assert git_runner.status_seen_paths == (
        ".git/config",
        "charts/app/Chart.yaml",
        "metadata/release.json",
    )


def test_handle_skips_commit_and_push_when_no_changes(tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    _write_file(source_dir / "charts/app/Chart.yaml", "apiVersion: v2\n")
    git_runner = FakeGitRunner(status_stdout="")
    publisher = _publisher(
        config=GitPublisherConfig(
            remote_url="https://gitlab.example.com/group/repo.git",
            branch_template="{project_name}",
        ),
        git_runner=git_runner,
    )

    result = publisher.handle(
        _request(source_dir, project_name="main", project_version="")
    )

    assert result.handled is False
    assert result.changed_file_count == 0
    assert result.commit_sha is None
    assert git_runner.commands == (
        (
            "clone",
            "--branch",
            "main",
            "--single-branch",
            "https://gitlab.example.com/group/repo.git",
            "repository",
        ),
        ("status", "--porcelain"),
    )


def test_handle_checks_out_existing_remote_branch(tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    _write_file(source_dir / "charts/app/Chart.yaml", "apiVersion: v2\n")
    git_runner = FakeGitRunner(
        status_stdout="A  charts/app/Chart.yaml\n",
        remote_branch_stdout="abc123\trefs/heads/my-project/1.2.3\n",
    )
    publisher = _publisher(
        config=GitPublisherConfig(
            remote_url="https://gitlab.example.com/group/repo.git",
        ),
        git_runner=git_runner,
    )

    publisher.handle(_request(source_dir))

    assert (
        "checkout",
        "-B",
        "my-project/1.2.3",
        "FETCH_HEAD",
    ) in git_runner.commands
    assert ("fetch", "origin", "my-project/1.2.3") in git_runner.commands


def test_handle_replaces_existing_worktree_content(tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    _write_file(source_dir / "charts/app/Chart.yaml", "apiVersion: v2\n")
    git_runner = FakeGitRunner(status_stdout="D  old.txt\nA  charts/app/Chart.yaml\n")
    publisher = _publisher(
        config=GitPublisherConfig(
            remote_url="https://gitlab.example.com/group/repo.git",
            branch_template="{project_name}",
        ),
        git_runner=git_runner,
    )

    publisher.handle(_request(source_dir, project_name="main", project_version=""))

    assert git_runner.status_seen_paths == (
        ".git/config",
        "charts/app/Chart.yaml",
    )


def test_handle_preserves_gitlab_ci_file(tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    _write_file(source_dir / "charts/app/Chart.yaml", "apiVersion: v2\n")
    git_runner = FakeGitRunner(
        status_stdout="A  charts/app/Chart.yaml\n",
        include_gitlab_ci=True,
    )
    publisher = _publisher(
        config=GitPublisherConfig(
            remote_url="https://gitlab.example.com/group/repo.git",
            branch_template="{project_name}",
        ),
        git_runner=git_runner,
    )

    publisher.handle(_request(source_dir, project_name="main", project_version=""))

    assert ".gitlab-ci.yml" in git_runner.status_seen_paths


def test_handle_rejects_missing_source_directory(tmp_path: Path) -> None:
    publisher = _publisher(git_runner=FakeGitRunner(status_stdout=""))

    with pytest.raises(FileNotFoundError, match="does not exist"):
        publisher.handle(_request(tmp_path / "missing"))


def test_handle_rejects_file_source_path(tmp_path: Path) -> None:
    source_path = tmp_path / "source"
    source_path.write_text("not a directory")
    publisher = _publisher(git_runner=FakeGitRunner(status_stdout=""))

    with pytest.raises(ValueError, match="not a directory"):
        publisher.handle(_request(source_path))


def test_handle_rejects_unknown_tenant_before_git_commands(tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    git_runner = FakeGitRunner(status_stdout="")
    publisher = _publisher(
        config=GitPublisherConfig(
            tenant_remote_urls={
                "tenant-a": "https://gitlab.example.com/group/tenant-a.git",
            },
        ),
        git_runner=git_runner,
    )

    with pytest.raises(KeyError, match="tenant-b"):
        publisher.handle(_request(source_dir, tenant_id="tenant-b"))

    assert git_runner.commands == ()


class FakeGitRunner:
    def __init__(
        self,
        *,
        status_stdout: str,
        remote_branch_stdout: str = "",
        include_gitlab_ci: bool = False,
    ) -> None:
        self._status_stdout = status_stdout
        self._remote_branch_stdout = remote_branch_stdout
        self._include_gitlab_ci = include_gitlab_ci
        self.commands: tuple[tuple[str, ...], ...] = ()
        self.clone_url = ""
        self.status_seen_paths: tuple[str, ...] = ()

    def run(
        self,
        args: tuple[str, ...],
        *,
        cwd: Path | None = None,
    ) -> GitCommandResult:
        self.commands = (*self.commands, args)

        if args[0] == "clone":
            if cwd is None:
                raise AssertionError("clone command requires cwd")

            self.clone_url = args[-2]
            repo_dir = cwd / args[-1]
            _write_file(repo_dir / ".git/config", "")
            _write_file(repo_dir / "old.txt", "old content")
            if self._include_gitlab_ci:
                _write_file(repo_dir / ".gitlab-ci.yml", "pipeline\n")
            return GitCommandResult(args, cwd, "", "")

        if args[:3] == ("ls-remote", "--heads", "origin"):
            return GitCommandResult(args, cwd, self._remote_branch_stdout, "")

        if args == ("status", "--porcelain"):
            if cwd is None:
                raise AssertionError("status command requires cwd")

            self.status_seen_paths = tuple(
                sorted(
                    str(path.relative_to(cwd))
                    for path in cwd.rglob("*")
                    if path.is_file()
                )
            )
            return GitCommandResult(args, cwd, self._status_stdout, "")

        if args == ("rev-parse", "HEAD"):
            return GitCommandResult(args, cwd, "abc123\n", "")

        return GitCommandResult(args, cwd, "", "")


def _write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def _publisher(
    *,
    git_runner: FakeGitRunner,
    config: GitPublisherConfig | None = None,
) -> GitPreparedBundleHandler:
    git_config = config or GitPublisherConfig(
        remote_url="https://gitlab.example.com/group/repo.git",
    )

    return GitPreparedBundleHandler(
        config=git_config,
        publish_target_resolver=MappingGitPublishTargetResolver(
            tenant_remote_urls=git_config.tenant_remote_urls or {},
            default_branch=git_config.branch,
            fallback_remote_url=git_config.remote_url,
        ),
        publish_branch_resolver=TemplateGitPublishBranchResolver(
            branch_template=git_config.branch_template,
        ),
        git_runner=git_runner,
    )


def _request(
    source_dir: Path,
    *,
    tenant_id: str = "tenant-a",
    project_name: str = "my-project",
    project_version: str = "1.2.3",
    bundle_name: str = "bundle.tar.gz",
) -> PreparedBundleRequest:
    return PreparedBundleRequest(
        source_dir=source_dir,
        tenant_id=tenant_id,
        project_name=project_name,
        project_version=project_version,
        remote_tarball_path=f"upload/{bundle_name}",
        bundle_name=bundle_name,
    )
