#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# demo-all-strategies.sh — exercise all five deployment strategies plus
# rollback, end to end. Run this once before submitting and capture the output
# (or a screen recording) as evidence.
#
#   export DOCKERHUB_USER=yourname
#   ./scripts/demo-all-strategies.sh
# ---------------------------------------------------------------------------
set -euo pipefail

: "${DOCKERHUB_USER:?Set DOCKERHUB_USER to your Docker Hub username}"
IMAGE="${DOCKERHUB_USER}/aceest-fitness"
OLD="3.1.2"
NEW="3.2.4"
NS="aceest"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

banner() { printf '\n\n\033[1;44m  %-70s\033[0m\n' "$*"; }
pause()  { echo; read -rp "Press Enter to continue… " _; }

banner "1/6  ROLLING UPDATE  ${OLD} -> ${NEW}  (zero downtime)"
"${ROOT}/scripts/deploy.sh" --strategy rolling --image "${IMAGE}:${OLD}" --version "${OLD}"
"${ROOT}/scripts/deploy.sh" --strategy rolling --image "${IMAGE}:${NEW}" --version "${NEW}"
kubectl -n "${NS}" rollout history deploy/aceest-fitness
pause

banner "2/6  ROLLBACK of the rolling update (back to ${OLD})"
"${ROOT}/scripts/rollback.sh" --strategy rolling
"${ROOT}/scripts/smoke-test.sh" --namespace "${NS}"
pause

banner "3/6  BLUE-GREEN  (deploy idle colour, verify, then promote)"
"${ROOT}/scripts/deploy.sh" --strategy blue-green --image "${IMAGE}:${NEW}" --version "${NEW}"
"${ROOT}/scripts/deploy.sh" --strategy blue-green --image "${IMAGE}:${NEW}" --version "${NEW}" --promote
kubectl -n "${NS}" get svc aceest-fitness-active -o jsonpath='{.spec.selector}'; echo
pause

banner "3b/6 BLUE-GREEN ROLLBACK (instant selector flip)"
"${ROOT}/scripts/rollback.sh" --strategy blue-green
pause

banner "4/6  CANARY  (10% -> 30% -> promote)"
"${ROOT}/scripts/deploy.sh" --strategy canary --image "${IMAGE}:${NEW}" --version "${NEW}"
"${ROOT}/scripts/canary-weight.sh" 30 "${NS}"
echo "Sampling 20 requests to show the traffic split:"
for _ in $(seq 1 20); do
  kubectl -n "${NS}" run curl-$RANDOM --rm -i --restart=Never --quiet \
    --image=curlimages/curl:8.11.0 -- \
    -fsS http://aceest-fitness.aceest.svc.cluster.local/version 2>/dev/null \
    | grep -o '"track": *"[^"]*"' || true
done | sort | uniq -c
"${ROOT}/scripts/deploy.sh" --strategy canary --image "${IMAGE}:${NEW}" --version "${NEW}" --promote
pause

banner "5/6  SHADOW  (mirrored traffic, zero user impact)"
"${ROOT}/scripts/deploy.sh" --strategy shadow --image "${IMAGE}:${NEW}" --version "${NEW}"
kubectl -n "${NS}" logs -l track=shadow --tail=20 || true
pause

banner "6/6  A/B TESTING  (header-based variant selection)"
"${ROOT}/scripts/deploy.sh" --strategy ab-testing --image "${IMAGE}:${NEW}" --version "${NEW}"
IP="$(minikube ip)"
echo "Control (variant A):"
curl -fsS -H 'Host: aceest.local' "http://${IP}/version"; echo
echo "Experiment (variant B):"
curl -fsS -H 'Host: aceest.local' -H 'X-Variant: B' "http://${IP}/version"; echo

banner "DONE — final cluster state"
kubectl -n "${NS}" get deploy,svc,ingress,pods -l app=aceest-fitness
