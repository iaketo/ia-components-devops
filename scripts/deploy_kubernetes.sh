#!/usr/bin/env bash
set -euo pipefail
: "${APP_IMAGE:?Definir APP_IMAGE con la imagen cargada en kind}"
# La sustitución solo admite caracteres de una referencia OCI, nunca código shell.
[[ "$APP_IMAGE" =~ ^[a-zA-Z0-9._/:-]+$ ]] || { echo 'Imagen inválida' >&2; exit 1; }
namespace=gmcomponents
mkdir -p reports/kubernetes
sed "s|gmcomponents-app:ep3|$APP_IMAGE|g" deploy/kubernetes/resources.yaml | kubectl apply -f -
configmap() {
  kubectl -n "$namespace" create configmap "$@" --dry-run=client -o yaml | kubectl apply -f -
}
configmap gmcomponents-env --from-literal=METRICS_ENABLED=true --from-literal=OBSERVABILITY_SELF_TEST="${EP3_SELF_TEST:-false}"
configmap gateway-config --from-file=default.conf=deploy/kubernetes/nginx.conf
configmap prometheus-config --from-file=prometheus.yml=deploy/kubernetes/prometheus.yml --from-file=alerts.yml=monitoring/alerts.yml
configmap blackbox-config --from-file=config.yml=monitoring/blackbox.yml
configmap loki-config --from-file=config.yml=deploy/kubernetes/loki.yml
configmap alloy-config --from-file=config.alloy=deploy/kubernetes/config.alloy
configmap alertmanager-config --from-file=config.yml=deploy/kubernetes/alertmanager.yml
configmap grafana-datasources --from-file=datasources.yml=deploy/kubernetes/datasources.yml
configmap grafana-provider --from-file=default.yml=monitoring/grafana/provisioning/dashboards/default.yml
configmap grafana-dashboard --from-file=ep3.json=deploy/kubernetes/dashboard.json
kubectl -n "$namespace" annotate deployment/gmcomponents "org.opencontainers.image.revision=${VCS_REF:-local}" --overwrite
for deployment in gmcomponents gateway prometheus blackbox pushgateway loki alloy alertmanager grafana; do
  kubectl -n "$namespace" rollout status "deployment/$deployment" --timeout=300s
done
for binding in gateway:8501:8080 prometheus:9090:9090 pushgateway:9091:9091 grafana:3000:3000 loki:3100:3100 alertmanager:9093:9093; do
  IFS=: read -r service local_port remote_port <<< "$binding"
  kubectl -n "$namespace" port-forward "service/$service" "$local_port:$remote_port" > "reports/kubernetes/port-forward-$service.log" 2>&1 &
  echo "$!" >> reports/kubernetes/port-forward.pids
done
