{{- define "kyverno-agent.name" -}}
{{- .Chart.Name }}
{{- end }}

{{- define "kyverno-agent.fullname" -}}
{{- printf "%s" .Chart.Name | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "kyverno-agent.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "kyverno-agent.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{- define "kyverno-agent.image" -}}
{{ .Values.image.repository }}:{{ .Values.image.tag | default .Chart.AppVersion }}
{{- end }}
