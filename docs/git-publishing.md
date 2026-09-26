# Git Publishing

The current release flow publishes extracted bundle content to Git instead of
launching AAP.

Git publishing is implemented by `GitPreparedBundleHandler`, which satisfies the
generic `PreparedBundleHandler` boundary. `TarballProcessor` prepares the bundle
content and metadata, then passes a `PreparedBundleRequest` to the handler.

## Target Repository Resolution

The watcher extracts `tenant_id` from the filename, then resolves the repository
URL from:

```text
GIT_TENANT_REMOTE_URLS_JSON
```

Example:

```text
GIT_TENANT_REMOTE_URLS_JSON={"mario":"https://gitlab.example.com/cd-dmz/mario.git"}
```

If a tenant is missing and `GIT_REMOTE_URL` is configured, the fallback URL is
used.

If no tenant mapping and no fallback are available, processing fails for that
record.

## Branch Resolution

The publish branch is created from filename metadata:

```text
GIT_BRANCH_TEMPLATE=release/{tenant_id}/{project_name}/{project_version}
```

For this file:

```text
mario-+frontend-+22.0.7-+20241028T115959.tar.gz.bundle
```

The branch becomes:

```text
release/mario/frontend/22.0.7
```

`GIT_BRANCH` is the base branch cloned before creating or checking out the
publish branch.

```text
GIT_BRANCH=main
```

## Authentication

For HTTPS repositories, set:

```text
GIT_USERNAME=git-user
GIT_PASSWORD=<password-or-token>
```

The handler injects the credentials into the clone URL. The Git command runner
masks configured secrets in command errors before logging or raising them.

Git commands are also run with interactive prompts disabled:

```text
GIT_TERMINAL_PROMPT=0
GIT_ASKPASS=
GCM_INTERACTIVE=never
```

This prevents the process from hanging while waiting for credentials.

## Publish Steps

For each processed bundle:

1. Clone `GIT_BRANCH` from the target repository.
2. Check whether the publish branch already exists on `origin`.
3. If it exists, fetch and check it out.
4. If it does not exist, create it from the cloned base branch.
5. Replace repository content with extracted bundle content.
6. Preserve `.git` and `.gitlab-ci.yml`.
7. Run `git status --porcelain`.
8. If there are changes, commit and push.
9. If there are no changes, skip commit and push.

## Preserved Files

The handler intentionally preserves:

```text
.git
.gitlab-ci.yml
```

`.gitlab-ci.yml` is kept because it contains the GitLab pipeline definition that
must remain available after the worktree content is replaced.

## Commit Message

The commit message is generated from the downloaded filename:

```text
Publish bundle <filename>
```

Example:

```text
Publish bundle mario-+frontend-+22.0.7-+20241028T115959.tar.gz.bundle
```

## No-Change Behavior

If `git status --porcelain` is empty after replacing content, the handler
returns without committing or pushing.

The result marks:

```text
handled=false
changed_file_count=0
commit_sha=null
```

For Git, `handled=false` means no Git commit or push was needed because the
prepared bundle content matched the repository content.

## Failure Debugging

When a Git command fails, the raised error includes:

```text
command
cwd
returncode
stderr
```

When a command times out, the error includes:

```text
command
cwd
timeout_seconds
stdout
stderr
```

Increase timeout if needed:

```text
GIT_TIMEOUT_SECONDS=120
```
