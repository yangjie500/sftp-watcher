# Configuration Reference

This page lists the environment variables accepted by `sftp-watcher`.

`Required` means the value must be set for that feature or authentication mode.
Values marked as secrets should be supplied through a secret manager, Kubernetes
Secret, or local `.env` file that is not committed.

## SFTP

| Variable | Required | Default | Example | Description |
| --- | --- | --- | --- | --- |
| `SFTP_HOST` | Yes | None | `sftp.example.com` | SFTP server hostname or IP address. |
| `SFTP_PORT` | No | `22` | `22` | SFTP server port. |
| `SFTP_USERNAME` | Yes | None | `sftp-user` | Username used to authenticate to SFTP. |
| `SFTP_PASSWORD` | When `SFTP_CREDENTIAL_SOURCE=config` | None | `<sftp-password>` | Password used for SFTP password authentication. Store as a secret. |
| `SFTP_PRIVATE_KEY_PATH` | No | None | `/etc/sftp/id_rsa` | Path to a private key for future key-based SFTP authentication support. |
| `SFTP_REMOTE_DIR` | Yes | None | `upload` | Remote directory to scan for bundles. |
| `SFTP_LOCAL_DIR` | Yes | None | `/data/watcher_local_directory` | Local directory where downloaded bundles are stored. |
| `SFTP_STATE_STORE_DIR` | Yes | None | `/data/watcher_state_store` | Local directory containing the download state database. |
| `SFTP_POLL_INTERVAL_SECONDS` | No | `10` | `10` | Delay between SFTP polling cycles. |
| `SFTP_WALK_MAX_DEPTH` | No | `1` | `3` | Maximum directory depth to walk under `SFTP_REMOTE_DIR`. |
| `SFTP_EXCLUDE_DIRS` | No | None | `archive,processed,failed` | Comma-separated remote directory names to skip while walking. |
| `SFTP_CREDENTIAL_SOURCE` | No | `config` | `config` | Source for SFTP credentials. Supported values are `config` and `cyberark_ccp`. |

## SFTP CyberArk CCP

These values are used when `SFTP_CREDENTIAL_SOURCE=cyberark_ccp`.

| Variable | Required | Default | Example | Description |
| --- | --- | --- | --- | --- |
| `SFTP_CYBERARK_CCP_BASE_URL` | Yes | None | `https://cyberark.example.com` | CyberArk CCP base URL. |
| `SFTP_CYBERARK_CCP_APP_ID` | Yes | None | `sftp-watcher` | CyberArk CCP application ID. |
| `SFTP_CYBERARK_CCP_SAFE` | Yes | None | `SFTP-SAFE` | CyberArk safe containing the SFTP credential. |
| `SFTP_CYBERARK_CCP_OBJECT_NAME` | Yes | None | `sftp-password-object` | CyberArk object name for the SFTP password. |
| `SFTP_CYBERARK_CCP_TIMEOUT_SECONDS` | No | `10` | `10` | CyberArk request timeout in seconds. |
| `SFTP_CYBERARK_CCP_VERIFY_TLS` | No | `true` | `true` | Whether to verify CyberArk TLS certificates. |
| `SFTP_CYBERARK_CCP_CA_BUNDLE_PATH` | No | None | `/etc/certs/company-ca.pem` | Optional custom CA bundle for CyberArk TLS verification. |
| `SFTP_CYBERARK_CCP_FOLDER` | No | None | `Root` | Optional CyberArk folder name. |
| `SFTP_CYBERARK_CCP_REASON` | No | None | `sftp-watcher` | Optional reason sent to CyberArk when retrieving credentials. |
| `SFTP_CYBERARK_CCP_CLIENT_CERT_PATH` | No | None | `/etc/certs/client.crt` | Optional client certificate path for mutual TLS. |
| `SFTP_CYBERARK_CCP_CLIENT_KEY_PATH` | No | None | `/etc/certs/client.key` | Optional client key path for mutual TLS. |

## Git Publishing

| Variable | Required | Default | Example | Description |
| --- | --- | --- | --- | --- |
| `GIT_TENANT_REMOTE_URLS_JSON` | Unless `GIT_REMOTE_URL` is set | None | `{"tenant-a":"https://gitlab.example.com/group/tenant-a.git"}` | JSON object mapping tenant IDs to Git remote URLs. |
| `GIT_REMOTE_URL` | Unless tenant mapping is used | None | `https://gitlab.example.com/group/default.git` | Fallback Git remote URL used when no tenant-specific URL is configured. |
| `GIT_BRANCH` | No | `main` | `main` | Source branch cloned before publishing bundle content. |
| `GIT_BRANCH_TEMPLATE` | No | `{project_name}/{project_version}` | `release/{tenant_id}/{project_name}/{project_version}` | Template used to generate the release branch name. |
| `GIT_USERNAME` | No | None | `git-user` | Optional username for Git HTTPS authentication. |
| `GIT_PASSWORD` | No | None | `<git-token>` | Optional password or token for Git HTTPS authentication. Store as a secret. |
| `GIT_AUTHOR_NAME` | No | `sftp-watcher` | `sftp-watcher` | Git author name used for commits created by the watcher. |
| `GIT_AUTHOR_EMAIL` | No | `sftp-watcher@example.com` | `sftp-watcher@example.com` | Git author email used for commits created by the watcher. |
| `GIT_TIMEOUT_SECONDS` | No | `60` | `120` | Timeout for each Git command. |

## Bundle Processing

| Variable | Required | Default | Example | Description |
| --- | --- | --- | --- | --- |
| `BUNDLE_FILENAME_METADATA_SEPARATOR` | No | `-+` | `-+` | Separator used to extract filename metadata from bundle names. Must not be empty or whitespace. |
| `BUNDLE_CONTAINER_IMAGE_DIRS` | No | `images,image,container-images,oci-images` | `offline-images,image-archives` | Comma-separated directory names removed before publishing bundle content to Git. |

## Telemetry

| Variable | Required | Default | Example | Description |
| --- | --- | --- | --- | --- |
| `SFTP_WATCHER_TELEMETRY_ENABLED` | No | `true` | `false` | Enables OpenTelemetry trace and log export. |
| `SFTP_WATCHER_TELEMETRY_VERIFY_TLS` | No | `true` | `false` | Whether OTLP HTTPS exports verify TLS certificates. |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | When telemetry is enabled and SDK default is not suitable | OpenTelemetry SDK default | `http://localhost:4318` | OTLP endpoint for a collector or backend such as Dynatrace ActiveGate. |
| `OTEL_EXPORTER_OTLP_PROTOCOL` | No | OpenTelemetry SDK default | `http/protobuf` | OTLP protocol used by the OpenTelemetry SDK. |
| `OTEL_EXPORTER_OTLP_HEADERS` | No | None | `Authorization=Api-Token <token>` | Optional OTLP headers, commonly used for backend authentication. Store as a secret. |

## Logging

| Variable | Required | Default | Example | Description |
| --- | --- | --- | --- | --- |
| `SFTP_WATCHER_LOG_FILE` | No | None | `/data/logs/sftp-watcher.log` | Optional local log file path. Only logs are written locally, not traces. |

## Cleanup

| Variable | Required | Default | Example | Description |
| --- | --- | --- | --- | --- |
| `CLEANUP_LOCAL_FILES_ENABLED` | No | `true` | `true` | Enables cleanup of downloaded local files after retention expires. |
| `LOCAL_FILE_RETENTION_DAYS` | No | `30` | `30` | Number of days to keep local downloaded files. |
| `CLEANUP_INTERVAL_SECONDS` | No | `3600` | `3600` | Delay between cleanup cycles. |

## Legacy AAP

AAP settings are retained for deployments that still use the previous AAP
integration path.

| Variable | Required | Default | Example | Description |
| --- | --- | --- | --- | --- |
| `AAP_BASE_URL` | Yes for AAP usage | None | `https://awx.example.com` | Base URL for AAP or AWX. |
| `AAP_JOB_TEMPLATE_ID` | Yes for AAP usage | None | `11` | Job template or workflow template ID to launch. |
| `AAP_AUTH_METHOD` | No | `token` | `basic` | AAP authentication mode. Supported values are `token` and `basic`. |
| `AAP_TOKEN` | When `AAP_CREDENTIAL_SOURCE=config` and `AAP_AUTH_METHOD=token` | None | `<aap-token>` | Token used for AAP token authentication. Store as a secret. |
| `AAP_USERNAME` | When `AAP_AUTH_METHOD=basic` | None | `admin` | Username used for AAP basic authentication. |
| `AAP_PASSWORD` | When `AAP_CREDENTIAL_SOURCE=config` and `AAP_AUTH_METHOD=basic` | None | `<aap-password>` | Password used for AAP basic authentication. Store as a secret. |
| `AAP_TIMEOUT_SECONDS` | No | `30` | `30` | AAP request timeout in seconds. |
| `AAP_VERIFY_TLS` | No | `true` | `false` | Whether to verify AAP TLS certificates. |
| `AAP_CA_BUNDLE_PATH` | No | None | `/etc/certs/company-ca-bundle.pem` | Optional custom CA bundle for AAP TLS verification. |
| `AAP_CREDENTIAL_SOURCE` | No | `config` | `cyberark_ccp` | Source for AAP credentials. Supported values are `config` and `cyberark_ccp`. |

## AAP CyberArk CCP

These values are used when `AAP_CREDENTIAL_SOURCE=cyberark_ccp`.

| Variable | Required | Default | Example | Description |
| --- | --- | --- | --- | --- |
| `AAP_CYBERARK_CCP_BASE_URL` | Yes | None | `https://cyberark.example.com` | CyberArk CCP base URL. |
| `AAP_CYBERARK_CCP_APP_ID` | Yes | None | `sftp-watcher` | CyberArk CCP application ID. |
| `AAP_CYBERARK_CCP_SAFE` | Yes | None | `AAP-SAFE` | CyberArk safe containing the AAP credential. |
| `AAP_CYBERARK_CCP_OBJECT_NAME` | Yes | None | `aap-password-object` | CyberArk object name for the AAP password or token. |
| `AAP_CYBERARK_CCP_TIMEOUT_SECONDS` | No | `10` | `10` | CyberArk request timeout in seconds. |
| `AAP_CYBERARK_CCP_VERIFY_TLS` | No | `true` | `true` | Whether to verify CyberArk TLS certificates. |
| `AAP_CYBERARK_CCP_CA_BUNDLE_PATH` | No | None | `/etc/certs/company-ca.pem` | Optional custom CA bundle for CyberArk TLS verification. |
| `AAP_CYBERARK_CCP_FOLDER` | No | None | `Root` | Optional CyberArk folder name. |
| `AAP_CYBERARK_CCP_REASON` | No | None | `sftp-watcher` | Optional reason sent to CyberArk when retrieving credentials. |
| `AAP_CYBERARK_CCP_CLIENT_CERT_PATH` | No | None | `/etc/certs/client.crt` | Optional client certificate path for mutual TLS. |
| `AAP_CYBERARK_CCP_CLIENT_KEY_PATH` | No | None | `/etc/certs/client.key` | Optional client key path for mutual TLS. |
