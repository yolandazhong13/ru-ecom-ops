{{/*
Expand the name of the chart.
*/}}
{{- define "ru-ecom-ops.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "ru-ecom-ops.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "ru-ecom-ops.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "ru-ecom-ops.labels" -}}
helm.sh/chart: {{ include "ru-ecom-ops.chart" . }}
{{ include "ru-ecom-ops.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "ru-ecom-ops.selectorLabels" -}}
app.kubernetes.io/name: {{ include "ru-ecom-ops.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "ru-ecom-ops.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "ru-ecom-ops.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Get environment-specific values
*/}}
{{- define "ru-ecom-ops.envValues" -}}
{{- if eq .Values.global.environment "development" }}
{{- .Values.development }}
{{- else if eq .Values.global.environment "staging" }}
{{- .Values.staging }}
{{- else }}
{{- . }}
{{- end }}
{{- end }}
