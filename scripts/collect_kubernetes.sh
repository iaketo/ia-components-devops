#!/usr/bin/env bash
set -euo pipefail
mkdir -p reports/kubernetes
if kubectl get namespace gmcomponents >/dev/null 2>&1; then
  kubectl get nodes -o wide > reports/kubernetes/nodes.txt
  kubectl version -o json > reports/kubernetes/version.json
  kubectl -n gmcomponents get deployments,pods,services -o json > reports/kubernetes/resources.json
  kubectl -n gmcomponents get events --sort-by=.lastTimestamp > reports/kubernetes/events.txt
  kubectl -n gmcomponents logs -l app=gmcomponents --all-containers=true --prefix=true --tail=200 > reports/kubernetes/application.log
  kubectl -n gmcomponents logs deployment/alloy --tail=100 > reports/kubernetes/alloy.log
  kubectl -n gmcomponents logs deployment/loki --tail=100 > reports/kubernetes/loki.log
fi
