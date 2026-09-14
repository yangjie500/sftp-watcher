# Operations

This document covers day-to-day checks and recovery actions for the watcher.

## Start Locally

Run with the default `.env` file:

```bash
sftp-watcher
```

Run with a specific environment file:

```bash
sftp-watcher --env-file .env.local
```

## Check Logs

The app always logs to console. If configured, it also writes to:

```text
SFTP_WATCHER_LOG_FILE
```

Useful log messages to look for:

```text
Resolved Git publish target
Extracted bundle
Removed container image artifacts
Expanded packaged Helm charts
Wrote release manifest
Published bundle content to Git
```

## Check State Database

The state database is:

```text
<SFTP_STATE_STORE_DIR>/download_state.sqlite3
```

The project provides a small admin CLI:

```bash
sftp-watcher-db list --db-dir ./testing-state
```

Filter by process state:

```bash
sftp-watcher-db list --db-dir ./testing-state --state pending
sftp-watcher-db list --db-dir ./testing-state --state success
sftp-watcher-db list --db-dir ./testing-state --state failed
```

## Retry a File

A file is identified by:

```text
remote_path
size
mtime
```

Mark a failed or successful record back to pending:

```bash
sftp-watcher-db mark-pending \
  --db-dir ./testing-state \
  --remote-path upload/mario-+frontend-+22.0.7.tar.gz.bundle \
  --size 123456 \
  --mtime 1720000000
```

The next processing cycle can then pick it up again.

## Mark a Record Manually

Mark success:

```bash
sftp-watcher-db mark-success \
  --db-dir ./testing-state \
  --remote-path upload/file.tar.gz.bundle \
  --size 123456 \
  --mtime 1720000000
```

Mark failed:

```bash
sftp-watcher-db mark-failed \
  --db-dir ./testing-state \
  --remote-path upload/file.tar.gz.bundle \
  --size 123456 \
  --mtime 1720000000
```

## Confirm Telemetry Export

Check the app logs first. If the collector is down and telemetry is enabled,
export failures can appear in the logs.

To avoid collector-related noise while debugging other issues:

```text
SFTP_WATCHER_TELEMETRY_ENABLED=false
```

For Dynatrace ActiveGate, confirm:

```text
OTEL_EXPORTER_OTLP_ENDPOINT
OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
OTEL_EXPORTER_OTLP_HEADERS=Authorization=Api-Token <token>
SFTP_WATCHER_TELEMETRY_VERIFY_TLS
```

## Common Failures

`No Git remote URL configured for tenant_id=...`

The tenant id extracted from the filename is not present in
`GIT_TENANT_REMOTE_URLS_JSON`, and `GIT_REMOTE_URL` fallback is not configured.

`Could not find nested tarball next to signature file`

The outer bundle has a signature file, but no tarball exists in the same
directory.

`Outer bundle does not contain a signature file`

The outer bundle does not include `.sig`, `.signature`, or `.asc`.

`Git command timed out`

The Git operation exceeded `GIT_TIMEOUT_SECONDS`. Check network access, Git
credentials, remote repository availability, and whether the repository is large.

`TIMESTAMP.json missing required keys`

The optional metadata file exists but does not contain both `TIMEDATE` and
`SIZEOFFILE`. The processor logs this and continues.

## Safe Manual Database Changes

Prefer `sftp-watcher-db` for state changes. If SQLite must be edited manually,
stop the watcher first or ensure no process is writing to the database. The app
uses WAL mode and a busy timeout, but manual writes during processing can still
make debugging confusing.
