# Deployment

This project includes a Helm chart under `charts/sftp-watcher`.

## Build Inputs

The chart expects an application image:

```yaml
image:
  repository: ghcr.io/yangjie500/sftp-watcher
  tag: "2.0.0"
```

Update the image tag manually when promoting a new release.

## Required Helm Values

Set the SFTP connection:

```yaml
config:
  sftp:
    host: "sftp.example.com"
    port: 22
    username: "sftp-user"
    remoteDir: "upload"
    localDir: /data/watcher_local_directory
    state_store_dir: /data/watcher_state_store
    credentialSource: config
```

Set the SFTP password in the chart secret values:

```yaml
secret:
  sftpPassword: "<sftp-password>"
```

Set Git publishing:

```yaml
config:
  git:
    tenantRemoteUrls:
      tenant-a: https://gitlab.example.com/group/tenant-a.git
    branch: main
    branchTemplate: "release/{tenant_id}/{project_name}/{project_version}"
    username: git-user
    authorName: sftp-watcher
    authorEmail: sftp-watcher@example.com

secret:
  gitPassword: "<git-password-or-token>"
```

`tenantRemoteUrls` is rendered as `GIT_TENANT_REMOTE_URLS_JSON`.

Set bundle parsing options:

```yaml
config:
  bundle:
    filenameMetadataSeparator: "-+"
    containerImageDirs:
      - images
      - image
      - container-images
      - oci-images
```

## Persistence

Persistence should normally be enabled:

```yaml
persistence:
  enabled: true
  downloadedFiles:
    size: 5Gi
  stateStore:
    size: 1Gi
```

The downloaded files volume backs `SFTP_LOCAL_DIR`. The state store volume backs
`SFTP_STATE_STORE_DIR` and contains `download_state.sqlite3`.

## Database Migration

The chart has a migration step:

```yaml
migrations:
  enabled: true
  command:
    - alembic
  args:
    - upgrade
    - head
```

Keep this enabled unless the target environment runs migrations separately.

## Telemetry

To use a normal OTLP collector:

```yaml
config:
  telemetry:
    enabled: true
    otlpEndpoint: "http://otel-collector:4318"
    otlpProtocol: "http/protobuf"
    verifyTls: true
```

To use Dynatrace ActiveGate:

```yaml
config:
  telemetry:
    enabled: true
    otlpEndpoint: "https://activegate.example.com/e/<environment-id>/api/v2/otlp"
    otlpProtocol: "http/protobuf"
    verifyTls: true

secret:
  otlpHeaders: "Authorization=Api-Token <dynatrace-token>"
```

If the ActiveGate uses a self-signed certificate and no CA bundle is available,
set `verifyTls: false`.

To disable telemetry:

```yaml
config:
  telemetry:
    enabled: false
```

## Local File Logs

To write logs to a file in the pod:

```yaml
config:
  logging:
    file: /data/logs/sftp-watcher.log
```

Make sure the path is backed by a writable volume if the log must survive pod
restart.

## Deploy

Render the chart locally:

```bash
helm template sftp-watcher charts/sftp-watcher
```

Install or upgrade:

```bash
helm upgrade --install watcher ./charts/sftp-watcher \
  --namespace sftp-watcher \
  --create-namespace \
  -f ./charts/sftp-watcher/values.yaml
```

## Database Admin UI

The chart can deploy `sqlite-web` for inspecting the state database:

```yaml
databaseAdmin:
  enabled: true
```

The default database path is:

```text
/data/watcher_state_store/download_state.sqlite3
```

Enable it only in environments where exposing a database admin UI is acceptable.
