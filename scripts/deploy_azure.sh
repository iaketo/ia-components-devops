#!/usr/bin/env bash
# Runs only on the Azure server, from the reviewed commit bundle.
set -euo pipefail
: "${APP_IMAGE:?}" "${VCS_REF:?}"
[[ "$APP_IMAGE" =~ ^ghcr\.io/iaketo/ia-components-devops@sha256:[a-f0-9]{64}$ ]]
[[ "$VCS_REF" =~ ^[a-f0-9]{40}$ ]]
ns=gmcomponents
started=$(date +%s)
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
kubectl get namespace "$ns" >/dev/null
cm() { kubectl -n "$ns" create configmap "$@" --dry-run=client -o yaml | kubectl apply -f -; }
cm gmcomponents-env --from-literal=METRICS_ENABLED=true --from-literal=OBSERVABILITY_SELF_TEST=false
cm gateway-config --from-file=default.conf=deploy/kubernetes/nginx.conf
cm prometheus-config --from-file=prometheus.yml=deploy/kubernetes/prometheus.yml --from-file=alerts.yml=monitoring/alerts.yml
cm blackbox-config --from-file=config.yml=monitoring/blackbox.yml
cm loki-config --from-file=config.yml=deploy/kubernetes/loki.yml
cm alloy-config --from-file=config.alloy=deploy/kubernetes/config.alloy
cm alertmanager-config --from-file=config.yml=deploy/kubernetes/alertmanager.yml
cm grafana-datasources --from-file=datasources.yml=deploy/kubernetes/datasources.yml
cm grafana-provider --from-file=default.yml=monitoring/grafana/provisioning/dashboards/default.yml
cm grafana-dashboard --from-file=ep3.json=deploy/kubernetes/dashboard.json
# Keep the kind manifests unchanged; render cloud-specific overrides only here.
python3 - <<'PY' | kubectl apply -f -
import os, hashlib, pathlib, yaml
p = pathlib.Path('deploy/kubernetes')
docs = list(yaml.safe_load_all((p / 'resources.yaml').read_text()))
paths = [*p.glob('*'), pathlib.Path('monitoring/alerts.yml'), pathlib.Path('monitoring/blackbox.yml'), pathlib.Path('monitoring/grafana/provisioning/dashboards/default.yml')]
h = hashlib.sha256()
for f in sorted(paths):
    if f.is_file():
        h.update(f.read_bytes())
claims = []
for doc in docs:
    if doc and doc.get('kind') == 'Deployment':
        template = doc['spec']['template']
        template['metadata'].setdefault('annotations', {})['gmcomponents/config-sha'] = h.hexdigest()
        name = doc['metadata']['name']
        if name in {'prometheus', 'loki', 'grafana'}:
            volumes = template['spec']['volumes']
            volume = next(v for v in volumes if v['name'] == 'data')
            volume.pop('emptyDir', None)
            volume['persistentVolumeClaim'] = {'claimName': name + '-data'}
            doc['spec']['strategy'] = {'type': 'Recreate'}
            claims.append({'apiVersion':'v1','kind':'PersistentVolumeClaim','metadata':{'name':name+'-data','namespace':'gmcomponents'},'spec':{'accessModes':['ReadWriteOnce'],'storageClassName':'local-path','resources':{'requests':{'storage':'1Gi' if name=='grafana' else '5Gi'}}}})
        if name == 'gmcomponents':
            app = next(c for c in template['spec']['containers'] if c['name'] == 'app')
            app['image'] = os.environ['APP_IMAGE']
            app['imagePullPolicy'] = 'IfNotPresent'
            app.setdefault('envFrom', []).append({'secretRef': {'name': 'gmcomponents-external', 'optional': True}})
            template['metadata']['annotations']['org.opencontainers.image.revision'] = os.environ['VCS_REF']
print(yaml.safe_dump_all(docs[:1] + claims + docs[1:], sort_keys=False))
PY
kubectl -n "$ns" apply -f - <<'YAML'
apiVersion: v1
kind: Service
metadata:
  name: gateway-public
  namespace: gmcomponents
spec:
  type: NodePort
  selector:
    app: gateway
  ports:
    - name: http
      port: 8080
      targetPort: 8080
      nodePort: 30080
YAML
for deployment in gmcomponents gateway prometheus blackbox pushgateway loki alloy alertmanager grafana; do
  kubectl -n "$ns" rollout status deployment/"$deployment" --timeout=420s
done
# Check the exact image and each replica, not only the gateway.
test "$(kubectl -n "$ns" get deploy gmcomponents -o jsonpath='{.spec.template.spec.containers[?(@.name=="app")].image}')" = "$APP_IMAGE"
test "$(kubectl -n "$ns" get deploy gmcomponents -o jsonpath='{.status.readyReplicas}')" = 2
for pod in $(kubectl -n "$ns" get pods -l app=gmcomponents -o jsonpath='{.items[*].metadata.name}'); do
  kubectl -n "$ns" wait --for=condition=Ready pod/"$pod" --timeout=120s
done
curl -fsS --retry 8 --retry-connrefused http://127.0.0.1:30080/_stcore/health
mkdir -p reports/azure
python3 scripts/ci_metrics.py --coverage coverage.xml --deployment-seconds "$(( $(date +%s) - started ))" --output reports/azure/ci-metrics.prom
# Push metrics via an internal Service IP (never exposed on Azure).
push_ip=$(kubectl -n "$ns" get svc pushgateway -o jsonpath='{.spec.clusterIP}')
curl -fsS --retry 8 --retry-connrefused --data-binary @reports/azure/ci-metrics.prom "http://$push_ip:9091/metrics/job/gmcomponents-ci"
prom_ip=$(kubectl -n "$ns" get svc prometheus -o jsonpath='{.spec.clusterIP}')
grafana_ip=$(kubectl -n "$ns" get svc grafana -o jsonpath='{.spec.clusterIP}')
loki_ip=$(kubectl -n "$ns" get svc loki -o jsonpath='{.spec.clusterIP}')
python3 scripts/check_monitoring.py --url "http://$prom_ip:9090" --output reports/azure/monitoring.json
cat reports/azure/monitoring.json
curl -fsS "http://$grafana_ip:3000/api/health"
curl -fsS "http://$grafana_ip:3000/api/dashboards/uid/gmcomponents-kubernetes" >/dev/null
curl -fsS --retry 8 --retry-delay 5 "http://$loki_ip:3100/ready"
kubectl get nodes -o wide
kubectl -n "$ns" get deployments,pods,svc -o wide
printf '\nVerified revision: %s\nVerified image: %s\n' "$VCS_REF" "$APP_IMAGE"
