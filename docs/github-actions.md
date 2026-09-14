# GitHub Actions Pipelines

This document explains the GitHub Actions workflows used by this repository.

The main entry point is:

```text
.github/workflows/ci.yml
```

The other workflow files are reusable workflows called by `ci.yml`:

```text
.github/workflows/_tox.yml
.github/workflows/_test.yml
.github/workflows/_container.yml
.github/workflows/_dist.yml
.github/workflows/_release.yml
.github/workflows/_debug_container.yml
```

## Main CI Workflow

`ci.yml` is named `CI`.

It runs on:

- Pull requests.
- Pushes to `main`.
- Any Git tag.

```yaml
on:
  push:
    branches:
      - main
    tags:
      - '*'
  pull_request:
```

The workflow is split into these jobs:

- `lint`
- `test`
- `container`
- `dist`
- `release`

There is also a commented-out `debug_container` job.

## Pull Request Behavior

On pull requests, the workflow validates the code but does not publish releases.

Expected behavior:

1. Run lint and type checks.
2. Run tests across the configured Python versions.
3. Build the container image locally and test the CLI inside the image.
4. Build Python package artifacts.
5. Do not publish container images.
6. Do not create a GitHub Release.

This makes PRs suitable for validation before merge.

## Push To Main Behavior

On pushes to `main`, the workflow performs the same validation and build steps as
pull requests.

The container workflow logs in to GHCR for non-PR events, but image publishing is
still gated by tag-specific logic in `_container.yml`.

Expected behavior:

1. Run lint and type checks.
2. Run tests.
3. Build and smoke-test the container image.
4. Build distribution artifacts.
5. Do not create a GitHub Release unless the ref is a tag.

## Tag Behavior

Tags are the release path.

When a tag is pushed, the workflow:

1. Runs lint and type checks.
2. Runs tests.
3. Builds and publishes the container image if tests pass.
4. Builds Python distribution artifacts.
5. Creates a GitHub Release.

The release job only runs when:

```yaml
github.ref_type == 'tag'
```

## `lint` Job

Defined in:

```text
.github/workflows/ci.yml
```

Implemented by reusable workflow:

```text
.github/workflows/_tox.yml
```

The `lint` job calls:

```yaml
tox: pre-commit,type-checking
```

That means it runs:

- `pre-commit`
- `pyright`

The actual tox environments are defined in `pyproject.toml`.

Locally, the equivalent command is:

```bash
uv run --locked tox -e pre-commit,type-checking
```

## `_tox.yml`

`_tox.yml` is a reusable workflow for running one or more tox environments.

Inputs:

- `tox`: required string, passed to `tox -e`.

Steps:

1. Check out the repository.
2. Install `uv`.
3. Run:

```bash
uv run --locked tox -e <tox input>
```

This workflow is currently used by the `lint` job.

## `test` Job

Defined in:

```text
.github/workflows/ci.yml
```

Implemented by reusable workflow:

```text
.github/workflows/_test.yml
```

The test job runs as a matrix over:

```text
Python 3.11
Python 3.12
Python 3.13
Python 3.14
```

Current runner:

```text
ubuntu-latest
```

The workflow uses:

```bash
uv run --locked tox -e tests
```

The `tests` tox environment runs pytest with coverage and writes:

```text
cov.xml
```

The coverage report is uploaded to Codecov.

Locally, the equivalent command is:

```bash
uv run --locked tox -e tests
```

or:

```bash
tox -e tests
```

depending on how your local environment is set up.

## `_test.yml`

`_test.yml` is a reusable workflow for running the test suite.

Inputs:

- `python-version`
- `runs-on`

Important environment variables:

```yaml
PY_IGNORE_IMPORTMISMATCH: "1"
UV_PYTHON: ${{ inputs.python-version }}
```

Steps:

1. Check out the repository with full history.
2. Install `uv`.
3. Run tests through tox.
4. Upload `cov.xml` to Codecov.

Full history is used because versioning depends on Git tags.

## `container` Job

Defined in:

```text
.github/workflows/ci.yml
```

Implemented by reusable workflow:

```text
.github/workflows/_container.yml
```

The `container` job depends on:

```yaml
needs: test
```

It runs even if tests fail:

```yaml
if: always()
```

But the reusable workflow receives:

```yaml
publish: ${{ needs.test.result == 'success' }}
```

So publishing only happens when tests pass.

The job needs these permissions:

```yaml
contents: read
packages: write
```

## `_container.yml`

`_container.yml` builds and optionally publishes the runtime container image.

Steps:

1. Check out the repository with full history.
2. Set up Docker Buildx.
3. Log in to GitHub Container Registry for non-PR events.
4. Build the image and load it into the local Docker cache.
5. Test that the CLI works inside the image:

```bash
docker run --rm tag_for_testing --version
```

6. Generate container metadata and tags.
7. Push the image to GHCR only when:

```yaml
inputs.publish && github.ref_type == 'tag'
```

Published image names use:

```text
ghcr.io/${{ github.repository }}
```

Generated tags include:

- the Git tag
- `latest`

For example, pushing tag `1.3.0` should publish:

```text
ghcr.io/<owner>/<repo>:1.3.0
ghcr.io/<owner>/<repo>:latest
```

## `dist` Job

Defined in:

```text
.github/workflows/ci.yml
```

Implemented by reusable workflow:

```text
.github/workflows/_dist.yml
```

The `dist` job builds Python package artifacts.

## `_dist.yml`

`_dist.yml` builds and validates Python distribution artifacts.

Steps:

1. Check out the repository with full history.
2. Install `uv`.
3. Build source distribution and wheel:

```bash
uvx --from build pyproject-build
```

4. Upload the `dist` directory as a workflow artifact.
5. Check package metadata:

```bash
uvx twine check --strict dist/*
```

6. Install the produced wheel.
7. Verify the installed module can run:

```bash
python -m sftp_watcher --version
```

The workflow sets `SOURCE_DATE_EPOCH` from the latest commit timestamp to improve
build reproducibility.

## `release` Job

Defined in:

```text
.github/workflows/ci.yml
```

Implemented by reusable workflow:

```text
.github/workflows/_release.yml
```

The release job depends on:

```yaml
needs: [dist, test]
```

It only runs for tags:

```yaml
if: github.ref_type == 'tag'
```

It needs:

```yaml
contents: write
```

## `_release.yml`

`_release.yml` creates the GitHub Release.

Steps:

1. Download workflow artifacts.
2. If generated docs exist in an `html` directory, zip them as `docs.zip`.
3. Create a GitHub Release with all downloaded artifacts.
4. Generate release notes automatically.

The release is marked as prerelease if the tag name contains:

- `a`
- `b`
- `rc`

Examples:

```text
1.3.0a1  -> prerelease
1.3.0b1  -> prerelease
1.3.0rc1 -> prerelease
1.3.0    -> normal release
```

## `debug_container` Job

The debug container job is currently commented out in `ci.yml`.

If enabled, it would call:

```text
.github/workflows/_debug_container.yml
```

## `_debug_container.yml`

`_debug_container.yml` builds and publishes a debug image target from the
Dockerfile.

It publishes only on tags.

Generated debug tags include:

- `<tag>-debug`
- `latest-debug`

For example:

```text
ghcr.io/<owner>/<repo>:1.3.0-debug
ghcr.io/<owner>/<repo>:latest-debug
```

This is useful when the Dockerfile has a `debug` stage with extra tools for
manual troubleshooting.

## Release Flow Summary

To release a version:

1. Merge the release branch or feature branch into `main`.
2. Create and push a Git tag.
3. The CI workflow runs on the tag.
4. Tests must pass.
5. Container image is published to GHCR.
6. Python package artifacts are built.
7. GitHub Release is created with generated notes and artifacts.

The workflow does not automatically update Helm chart values or application
version references outside the Python package metadata. Those updates must be
handled separately if the release requires them.

## Common Failure Points

Common causes of pipeline failure:

- `pre-commit` formatting or lint failure.
- Pyright type-checking errors.
- Test failures on one Python version but not another.
- Missing or invalid lock file state for `uv run --locked`.
- Docker build failure.
- CLI smoke test failure inside the container.
- GHCR publish permission issue.
- Package metadata failure from `twine check`.
- Release creation permission issue.

For local debugging, start with:

```bash
uv run --locked tox -e pre-commit,type-checking
uv run --locked tox -e tests
docker build -t sftp-watcher:test .
docker run --rm sftp-watcher:test --version
```
