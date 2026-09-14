# Release Process

Use this checklist when preparing a new application release.

## Versioning

The Python package version is generated from Git tags by `setuptools_scm`.
Do not manually add a package version to `pyproject.toml`.

`uv.lock` is not updated by a release tag. Update it only when dependencies change.

## Before Merging

1. Create a release branch.
2. Make all code, chart, and documentation changes on the release branch.
3. If the default deployed image tag should change, update it manually in:

   ```text
   charts/sftp-watcher/values.yaml
   ```

   Example:

   ```yaml
   image:
     tag: "1.3.0"
   ```

4. If the Helm chart package version should change, update it manually in:

   ```text
   charts/sftp-watcher/Chart.yaml
   ```

   Example:

   ```yaml
   version: 0.1.0
   appVersion: "1.3.0"
   ```

5. Open a Pull Request into `main`.
6. Wait for CI to pass.

## Merge and Tag

After the Pull Request is merged:

```bash
git checkout main
git pull origin main
git tag 1.3.0
git push origin 1.3.0
```

Use the release version as the tag name. Existing tags use plain version numbers,
for example:

```text
1.1.0
```

## Expected Automation

Pushing the tag should trigger CI and release automation.

The release workflow should:

1. Build the Python source distribution and wheel.
2. Create a GitHub Release.
3. Build and publish the container image.
4. Publish container tags based on the Git tag and `latest`.

For tag `1.3.0`, expect container tags like:

```text
ghcr.io/yangjie500/sftp-watcher:1.3.0
ghcr.io/yangjie500/sftp-watcher:latest
```

## After Release

1. Check the GitHub Actions run for the tag.
2. Check that the GitHub Release was created.
3. Check that the container image tag exists in GHCR.
4. If deploying with Helm, confirm the chart values point to the intended image tag.
5. Deploy to a test environment before promoting further.

## Common Mistakes

- Do not expect `pyproject.toml` to be updated automatically with the release
  version. The version comes from the Git tag.
- Do not expect `uv.lock` to change during release. It changes only when
  dependencies are changed and locked again.
- Do not forget to update `charts/sftp-watcher/values.yaml` if the chart default
  image tag should move to the new version.
- Do not tag before the release Pull Request is merged into `main`.
