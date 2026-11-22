#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# codespaces-setup.sh — create the k3d Kubernetes cluster inside a Codespace.
#
#   bash scripts/codespaces-setup.sh           # create (idempotent)
#   RECREATE=1 bash scripts/codespaces-setup.sh  # destroy and rebuild
#
# Why k3d and not Minikube: k3d runs k3s inside Docker containers, starts in
# ~20 seconds, uses a fraction of the RAM, and — crucially — lets us map node
# ports straight onto the Codespace host so GitHub can forward them as public
# HTTPS URLs. Those URLs are what you submit as the cluster endpoints.
# ---------------------------------------------------------------------------
set -euo pipefail

CLUSTER="${CLUSTER:-aceest}"
log() { printf '\n\033[1;33m==> %s\033[0m\n' "$*"; }

if [[ "${RECREATE:-0}" == "1" ]]; then
  log "Deleting the existing cluster"
  k3d cluster delete "${CLUSTER}" || true
fi

if k3d cluster list "${CLUSTER}" >/dev/null 2>&1; then
  log "Cluster '${CLUSTER}' already exists — starting it if stopped"
  k3d cluster start "${CLUSTER}" || true
else
  log "Creating the k3d cluster '${CLUSTER}'"
  # A single server node keeps NodePort routing deterministic: every pod lands
  # on the one node whose ports are mapped to the Codespace host.
  # Traefik is disabled so that ingress-nginx can own the ingress class, which
  # is what the canary-weight and canary-by-header annotations require.
  k3d cluster create "${CLUSTER}" \
    --servers 1 --agents 0 \
    --k3s-arg "--disable=traefik@server:0" \
    --port "30080-30090:30080-30090@server:0" \
    --wait
fi

log "Waiting for the node to be ready"
kubectl wait --for=condition=Ready node --all --timeout=180s

log "Installing the NGINX ingress controller"
if ! kubectl get ns ingress-nginx >/dev/null 2>&1; then
  helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx >/dev/null
  helm repo update >/dev/null
  helm install ingress-nginx ingress-nginx/ingress-nginx \
    --namespace ingress-nginx --create-namespace \
    --set controller.service.type=NodePort \
    --set controller.service.nodePorts.http=30090 \
    --set controller.watchIngressWithoutClass=true \
    --set controller.admissionWebhooks.enabled=false \
    --set controller.resources.requests.cpu=50m \
    --set controller.resources.requests.memory=128Mi \
    --wait --timeout 5m
else
  echo "    ingress-nginx already installed"
fi

log "Applying the shared namespace, config and services"
kubectl apply -f k8s/base/namespace.yaml
kubectl -n aceest apply -f k8s/base/config.yaml
kubectl -n aceest apply -f k8s/base/service.yaml

log "Cluster ready"
kubectl get nodes
kubectl -n ingress-nginx get svc ingress-nginx-controller

cat <<'NOTE'

  Node ports 30080-30090 are mapped onto the Codespace host, so each one shows
  up in the PORTS tab of VS Code. To turn one into a submittable URL:

      PORTS tab -> right-click the port -> Port Visibility -> Public

  The public URL looks like:
      https://<your-codespace-name>-30080.app.github.dev

NOTE
