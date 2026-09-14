# Configuration

This application is configured through environment variables. Locally, the
default CLI entry point reads `.env` unless another file is provided with
`--env-file`.

```bash
sftp-watcher --env-file .env
```

For Kubernetes deployment, the Helm chart renders these values from
`charts/sftp-watcher/values.yaml` into a ConfigMap and Secret.

## SFTP

Required when using direct config credentials:

```text
SFTP_HOST=sftp.example.com
SFTP_PORT=22
SFTP_USERNAME=sftp-user
SFTP_PASSWORD=<password>
SFTP_REMOTE_DIR=upload
SFTP_LOCAL_DIR=/data/watcher_local_directory
SFTP_STATE_STORE_DIR=/data/watcher_state_store
```

Optional:

```text
SFTP_PRIVATE_KEY_PATH=/etc/sftp/key
SFTP_POLL_INTERVAL_SECONDS=10
SFTP_WALK_MAX_DEPTH=1
SFTP_EXCLUDE_DIRS=archive,processed,failed
```

`SFTP_LOCAL_DIR` stores downloaded files. `SFTP_STATE_STORE_DIR` stores the
SQLite database named `download_state.sqlite3`.

## Credentials

Credential source can be either `config` or `cyberark_ccp`.

```text
SFTP_CREDENTIAL_SOURCE=config
```

For CyberArk CCP:

```text
SFTP_CYBERARK_CCP_BASE_URL=https://cyberark.example.com
SFTP_CYBERARK_CCP_APP_ID=my-app-id
SFTP_CYBERARK_CCP_SAFE=SFTP-SAFE
SFTP_CYBERARK_CCP_OBJECT_NAME=sftp-password-object
SFTP_CYBERARK_CCP_TIMEOUT_SECONDS=10
SFTP_CYBERARK_CCP_VERIFY_TLS=true
SFTP_CYBERARK_CCP_CA_BUNDLE_PATH=/etc/certs/company-ca.pem
SFTP_CYBERARK_CCP_FOLDER=
SFTP_CYBERARK_CCP_REASON=
SFTP_CYBERARK_CCP_CLIENT_CERT_PATH=
SFTP_CYBERARK_CCP_CLIENT_KEY_PATH=
```

## Git Publishing

At least one Git target must be configured:

```text
GIT_TENANT_REMOTE_URLS_JSON={"tenant-a":"https://gitlab.example.com/group/tenant-a.git"}
```

Optional fallback repository:

```text
GIT_REMOTE_URL=https://gitlab.example.com/group/default.git
```

Publishing behavior:

```text
GIT_BRANCH=main
GIT_BRANCH_TEMPLATE=release/{tenant_id}/{project_name}/{project_version}
GIT_USERNAME=git-user
GIT_PASSWORD=<password-or-token>
GIT_AUTHOR_NAME=sftp-watcher
GIT_AUTHOR_EMAIL=sftp-watcher@example.com
GIT_TIMEOUT_SECONDS=60
```

`GIT_BRANCH` is the base branch cloned first. `GIT_BRANCH_TEMPLATE` is the
branch created or checked out for the release content.

## Bundle Processing

Container image directories are removed before publishing to Git.

```text
BUNDLE_CONTAINER_IMAGE_DIRS=images,image,container-images,oci-images
```

Packaged Helm charts with `.tgz` extension are expanded before publishing when
the archive contains a `Chart.yaml`.

## Telemetry

Telemetry can be turned off completely:

```text
SFTP_WATCHER_TELEMETRY_ENABLED=false
```

OTLP export settings:

```text
SFTP_WATCHER_TELEMETRY_VERIFY_TLS=true
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
OTEL_EXPORTER_OTLP_HEADERS=Authorization=Api-Token <token>
```

Set `SFTP_WATCHER_TELEMETRY_VERIFY_TLS=false` only when connecting to an HTTPS
collector or ActiveGate with a certificate that cannot be verified.

## Local Logging

Console logging is enabled by default. To also write logs to a local file:

```text
SFTP_WATCHER_LOG_FILE=/data/logs/sftp-watcher.log
```

Only logs are written to this file. Traces are exported through OpenTelemetry.

## Cleanup

Downloaded local files can be cleaned up automatically:

```text
CLEANUP_LOCAL_FILES_ENABLED=true
LOCAL_FILE_RETENTION_DAYS=30
CLEANUP_INTERVAL_SECONDS=3600
```

The cleanup lifecycle removes old downloaded files from `SFTP_LOCAL_DIR`.

## Legacy AAP Settings

The current Git publishing flow no longer launches AAP from the tarball
processor. Some AAP settings still exist in the codebase for compatibility with
older code paths and tests.

```text
AAP_BASE_URL=https://awx.example.com
AAP_JOB_TEMPLATE_ID=11
AAP_AUTH_METHOD=token
AAP_TOKEN=<token>
AAP_USERNAME=
AAP_PASSWORD=
AAP_TIMEOUT_SECONDS=30
AAP_VERIFY_TLS=true
```
