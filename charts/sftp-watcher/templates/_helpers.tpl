{{/*
Expand the name of the chart.
*/}}
{{- define "sftp-watcher.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "sftp-watcher.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "sftp-watcher.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Common labels.
*/}}
{{- define "sftp-watcher.labels" -}}
helm.sh/chart: {{ include "sftp-watcher.chart" . }}
{{ include "sftp-watcher.selectorLabels" . }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{/*
Selector labels.
*/}}
{{- define "sftp-watcher.selectorLabels" -}}
app.kubernetes.io/name: {{ include "sftp-watcher.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{/*
Create the name of the service account to use.
*/}}
{{- define "sftp-watcher.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
{{- default (include "sftp-watcher.fullname" .) .Values.serviceAccount.name -}}
{{- else -}}
{{- default "default" .Values.serviceAccount.name -}}
{{- end -}}
{{- end -}}

{{/*
Name of the secret containing runtime credentials.
*/}}
{{- define "sftp-watcher.secretName" -}}
{{- default (printf "%s-secret" (include "sftp-watcher.fullname" .)) .Values.secret.existingSecret -}}
{{- end -}}

{{/*
Name of the persistent volume claim for downloaded SFTP files.
*/}}
{{- define "sftp-watcher.downloadedFilesPvcName" -}}
{{- default (printf "%s-downloaded-files" (include "sftp-watcher.fullname" .)) .Values.persistence.downloadedFiles.existingClaim -}}
{{- end -}}

{{/*
Name of the persistent volume claim for watcher state.
*/}}
{{- define "sftp-watcher.stateStorePvcName" -}}
{{- default (printf "%s-state-store" (include "sftp-watcher.fullname" .)) .Values.persistence.stateStore.existingClaim -}}
{{- end -}}
