# SFTP Watcher Application Flow

This document explains how the SFTP watcher runs, how a bundle moves through the
application, and which configuration values control the Git publishing behavior.

## Purpose

The application watches an SFTP directory for new release bundles. When it finds a
new file, it downloads the file, records it in a local SQLite state database,
processes the release bundle, and publishes the processed content to a Git
repository.

The current bundle processing flow is aimed at deployment artifacts:

1. Download a tarball bundle from SFTP.
2. Extract the outer bundle and nested tarball.
3. Remove container image artifacts.
4. Expand packaged Helm charts from `.tgz` into directories.
5. Write a `release.json` manifest.
6. Push the remaining content to a tenant-specific Git repository and branch.

## Runtime Composition

Application startup is assembled in `src/sftp_watcher/app.py`.

At startup, the app builds:

- SFTP configuration from `SFTPWatcherConfig`.
- Git publishing configuration from `GitPublisherConfig`.
- Bundle processing configuration from `BundleProcessingConfig`.
- A `ParamikoSFTPClient` for SFTP operations.
- A SQLite-backed `DownloadStateService`.
- A `FileProcessorRouter` with `TarballProcessor`.
- Supporting processors:
  - `SafeTarBundleExtractor`
  - `ContainerImageRemovingBundleContentFilter`
  - `PackagedHelmChartExpander`
  - `ReleaseManifestWriter`
  - `GitRepositoryPublisher`

The main loop repeatedly calls:

```text
SFTPWatcher.poll_once()
```

and sleeps for `SFTP_POLL_INTERVAL_SECONDS` between poll cycles.

## Poll Lifecycle

Each watcher poll performs this sequence:

1. Run `before_poll` lifecycle hooks.
2. Connect to SFTP.
3. Process any records already marked `pending` in SQLite.
4. Walk the configured SFTP directory.
5. Build a `DownloadRecord` for each remote file.
6. Skip records already downloaded, based on path, size, and mtime.
7. Download new files to the local directory.
8. Mark downloaded files as `pending`.
9. Process each pending record.
10. Mark each record `success` or `failed`.
11. Close the SFTP connection.
12. Run `after_poll` lifecycle hooks.

Downloads are written to a temporary `*.tmp` file first and then moved into place.
This avoids leaving partially downloaded files at the final local path.

## State Store

The application uses SQLite to remember downloaded files and processing state.

The state store prevents duplicate processing and allows recovery after restarts.
If the app stops after download but before processing completes, the record remains
`pending`. The next poll processes old pending records before looking for new
remote files.

The main process states are:

- `pending`: downloaded but not successfully processed yet
- `success`: processed and published successfully
- `failed`: processing failed or no processor handled the file

## File Processing Router

The `FileProcessorRouter` chooses the first processor that can handle a downloaded
record.

Currently the main processor is `TarballProcessor`. It accepts local files that
look like tar archives or gzip archives based on file magic bytes.

## Bundle Processing Flow

`TarballProcessor` performs the release-bundle processing work.

The processing sequence is:

1. Start the `sftp_watcher.process_tarball` span.
2. Extract optional `TIMESTAMP.json` metadata from the tarball.
3. Extract filename metadata.
4. Resolve the tenant Git repository.
5. Resolve the target Git branch.
6. Extract the outer bundle and nested tarball.
7. Remove configured container image directories.
8. Expand packaged Helm chart `.tgz` files.
9. Write `release.json`.
10. Publish the prepared directory to Git.

## Filename Metadata

The processor extracts these metadata values from the bundle filename:

```text
tenant_id
project_name
project_version
```

The filename may contain additional metadata after those fields. Additional values
are ignored by the filename metadata extractor.

Example intended filename shape:

```text
mario-+frontend-+22.0.7-+20241028T115959.tar.gz.bundle
```

That should produce:

```json
{
  "tenant_id": "mario",
  "project_name": "frontend",
  "project_version": "22.0.7"
}
```

Important: the separator used by the runtime code and the filename convention
must match. Check `TarballProcessor.FILENAME_METADATA_SEPARATOR` when changing the
filename format.

## Release Manifest

Before publishing to Git, the app writes `release.json` at the root of the
prepared extracted directory.

Example:

```json
{
  "tenant_id": "mario",
  "project_name": "frontend",
  "project_version": "22.0.7",
  "remote_tarball_path": "upload/mario-+frontend-+22.0.7-+20241028T115959.tar.gz.bundle"
}
```

This file is generated from filename metadata and the original SFTP remote path.

## Helm Chart Expansion

The app expands packaged Helm chart archives before publishing to Git.

`PackagedHelmChartExpander` scans the extracted bundle directory for `*.tgz`.
For each `.tgz` file:

- If the archive contains `Chart.yaml`, it is treated as a Helm chart package.
- The archive is safely extracted into the archive's parent directory.
- The original `.tgz` package is removed after successful extraction.
- Non-Helm `.tgz` files are ignored.
- Unsafe paths such as `../file` are rejected.

This means Git should receive expanded chart directories instead of packaged chart
archives.

## Container Image Removal

`ContainerImageRemovingBundleContentFilter` removes directories that are treated
as container image payloads.

The default directory names are:

```text
images
image
container-images
oci-images
```

Override them with:

```env
BUNDLE_CONTAINER_IMAGE_DIRS=images,image,container-images,oci-images
```

Only directories with matching names are removed. Helm chart `.tgz` files outside
those image directories are left for the Helm chart expansion step.

## Git Repository Selection

The target Git repository is selected by tenant ID.

Configure the mapping with:

```env
GIT_TENANT_REMOTE_URLS_JSON={"mario":"https://gitlab.com/cd-dmz/mario/mario-dmz.git"}
```

If a tenant is not found in the mapping, the app can use an optional fallback:

```env
GIT_REMOTE_URL=https://gitlab.example.com/group/default.git
```

If neither a tenant mapping nor fallback URL exists, processing fails for that
file.

## Git Branch Selection

`GIT_BRANCH` is the base branch cloned before publishing.

Example:

```env
GIT_BRANCH=main
```

The publish branch is generated from filename metadata using
`GIT_BRANCH_TEMPLATE`.

Example:

```env
GIT_BRANCH_TEMPLATE=release/{tenant_id}/{project_name}/{project_version}
```

For:

```text
mario-+frontend-+22.0.7-+20241028T115959.tar.gz.bundle
```

the generated publish branch is:

```text
release/mario/frontend/22.0.7
```

The branch name is validated before Git publish. Invalid Git branch names fail
processing.

## Git Publish Behavior

`GitRepositoryPublisher` publishes prepared content to Git.

The Git flow is:

1. Clone the configured base branch into a temporary directory.
2. Check whether the dynamic publish branch already exists.
3. If it exists, fetch it and check it out.
4. If it does not exist, create it from the base branch.
5. Replace the repository worktree content with the prepared bundle content.
6. Preserve `.git` and `.gitlab-ci.yml`.
7. Commit changes if there are any.
8. Push the dynamic branch to origin.

`.gitlab-ci.yml` is preserved so GitLab pipeline configuration remains available
on release branches.

## Git Authentication

For HTTPS Git remotes, configure:

```env
GIT_USERNAME=<username-or-token-name>
GIT_PASSWORD=<token-or-password>
```

The publisher injects these credentials into the clone URL internally. The Git
command runner masks configured secrets in errors.

Use:

```env
GIT_TIMEOUT_SECONDS=60
```

to control the timeout for each Git command.

## Observability

The app creates spans for the main processing stages:

- `sftp_watcher.file_flow`
- `sftp_watcher.download_file`
- `sftp_watcher.process_file`
- `sftp_watcher.route_file`
- `sftp_watcher.process_tarball`

Important span attributes include:

- `sftp.remote_path`
- `sftp.local_path`
- `sftp.file.size`
- `tenant.id`
- `project.name`
- `project.version`
- `git.remote_url`
- `git.branch`
- `git.changed_file_count`
- `git.pushed`
- `git.commit_sha`
- `helm_chart.expanded_count`
- `helm_chart.removed_package_count`
- `release_manifest.path`

Telemetry can be disabled with:

```env
SFTP_WATCHER_TELEMETRY_ENABLED=false
```

## Local Logging

Console logging is configured at startup. A file log can also be enabled with:

```env
SFTP_WATCHER_LOG_FILE=./sftp-watcher.log
```

## Minimal Configuration Example

```env
SFTP_HOST=192.168.2.4
SFTP_PORT=22
SFTP_USERNAME=sftp_user
SFTP_PASSWORD=secret
SFTP_REMOTE_DIR=upload
SFTP_LOCAL_DIR=./testing-ground
SFTP_STATE_STORE_DIR=./testing-state
SFTP_POLL_INTERVAL_SECONDS=10
SFTP_WALK_MAX_DEPTH=3

GIT_TENANT_REMOTE_URLS_JSON={"mario":"https://gitlab.com/cd-dmz/mario/mario-dmz.git"}
GIT_BRANCH=main
GIT_BRANCH_TEMPLATE=release/{tenant_id}/{project_name}/{project_version}
GIT_USERNAME=git-user
GIT_PASSWORD=git-token
GIT_AUTHOR_NAME=sftp-watcher
GIT_AUTHOR_EMAIL=sftp-watcher@example.com
GIT_TIMEOUT_SECONDS=60

BUNDLE_CONTAINER_IMAGE_DIRS=images,image,container-images,oci-images
```

## Failure Handling

If processing fails, the watcher catches the exception, records it on the active
span, marks the record as `failed`, and continues polling.

Common failure cases:

- Missing or invalid SFTP credentials.
- Git remote URL missing for a tenant.
- Git authentication failure.
- Missing base branch.
- Invalid dynamic branch name.
- Unsafe tar path in a bundle or Helm chart package.
- Invalid tarball contents.
- No processor accepts the downloaded file.

Failed records can be inspected through the SQLite state store or the admin CLI.
