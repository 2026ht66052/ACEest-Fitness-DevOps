#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# minikube-setup.sh — one-shot local cluster bootstrap.
#
#   ./scripts/minikube-setup.sh
#
# Starts Minikube, enables the ingress + metrics addons (needed for the
# A/B, canary and shadow strategies and for the HPA), creates the namespace
# and prints the URLs you will submit.
# ---------------------------------------------------------------------------
set -euo pipefail

PROFILE="${PROFILE:-aceest}"
CPUS="${CPUS:-4}"
MEMORY="${MEMORY:-6144}"
K8S_VERSION="${K8S_VERSION:-v1.31.0}"

log() { printf '\n\033[1;33m==> %s\033[0m\n' "$*"; }

log "Starting Minikube profile '${PROFILE}'"
minikube start \
  --profile "${PROFILE}" \
  --cpus "${CPUS}" \
  --memory "${MEMORY}" \
  --kubernetes-version "${K8S_VERSION}" \
  --driver docker

minikube profile "${PROFILE}"

log "Enabling addons"
minikube addons enable ingress   --profile "${PROFILE}"
minikube addons enable metrics-server --profile "${PROFILE}"

log "Creating namespace and shared resources"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
kubectl apply -f "${ROOT}/k8s/base/namespace.yaml"
kubectl -n aceest apply -f "${ROOT}/k8s/base/config.yaml"
kubectl -n aceest apply -f "${ROOT}/k8s/base/service.yaml"

IP="$(minikube ip --profile "${PROFILE}")"

log "Cluster ready"
cat <<EOF

  Minikube IP        : ${IP}
  Add to /etc/hosts  : ${IP}  aceest.local

  Endpoints once deployed:
    Dashboard (rolling)   http://${IP}:30080/
    Blue-green active     http://${IP}:30081/version
    Blue preview          http://${IP}:30082/version
    Green preview         http://${IP}:30083/version
    Canary direct         http://${IP}:30084/version
    A/B variant A         http://${IP}:30085/version
    A/B variant B         http://${IP}:30086/version
    Ingress (host header) curl -H 'Host: aceest.local' http://${IP}/version
    A/B via header        curl -H 'Host: aceest.local' -H 'X-Variant: B' http://${IP}/version

  Next:
    ./scripts/deploy.sh --strategy rolling --image <user>/aceest-fitness:3.2.4 --version 3.2.4

EOF
