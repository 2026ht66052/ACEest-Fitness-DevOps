#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# smoke-test.sh — verify a deployed version from inside the cluster.
#
# A throwaway curl pod hits the target service, so the test works identically
# on Minikube, EKS, AKS and GKE without needing an external IP or ingress.
#
#   ./scripts/smoke-test.sh --namespace aceest --expect-version 3.2.4
#   ./scripts/smoke-test.sh --service aceest-fitness-canary --expect-version 3.2.4
# ---------------------------------------------------------------------------
set -euo pipefail

NAMESPACE="aceest"
SERVICE="aceest-fitness"
EXPECT_VERSION=""
RETRIES=20

while [[ $# -gt 0 ]]; do
  case "$1" in
    --namespace)      NAMESPACE="$2"; shift 2 ;;
    --service)        SERVICE="$2"; shift 2 ;;
    --expect-version) EXPECT_VERSION="$2"; shift 2 ;;
    --retries)        RETRIES="$2"; shift 2 ;;
    -h|--help)        sed -n '2,12p' "$0"; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done

BASE="http://${SERVICE}.${NAMESPACE}.svc.cluster.local"
POD="smoke-test-$$"
log() { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }

cleanup() { kubectl -n "${NAMESPACE}" delete pod "${POD}" --ignore-not-found --wait=false >/dev/null 2>&1 || true; }
trap cleanup EXIT

probe() {
  kubectl -n "${NAMESPACE}" run "${POD}" --rm -i --restart=Never \
    --image=curlimages/curl:8.11.0 --quiet --command -- \
    sh -c "
      set -e
      for i in \$(seq 1 ${RETRIES}); do
        if curl -fsS --max-time 5 ${BASE}/health >/dev/null 2>&1; then break; fi
        sleep 3
      done
      echo '--- /health  ---'; curl -fsS --max-time 5 ${BASE}/health;  echo
      echo '--- /ready   ---'; curl -fsS --max-time 5 ${BASE}/ready;   echo
      echo '--- /version ---'; curl -fsS --max-time 5 ${BASE}/version; echo
      echo '--- GET /api/v1/programs ---'
      curl -fsS --max-time 5 ${BASE}/api/v1/programs | head -c 200; echo
      echo '--- POST /api/v1/bmi ---'
      curl -fsS --max-time 5 -X POST ${BASE}/api/v1/bmi \
        -H 'Content-Type: application/json' -d '{\"height\":175,\"weight\":80}'; echo
      echo '--- GET / (UI) ---'
      curl -fsS -o /dev/null -w 'dashboard HTTP %{http_code}\n' --max-time 5 ${BASE}/
    "
}

log "Smoke testing ${BASE}"
OUTPUT="$(probe)"
echo "${OUTPUT}"

echo "${OUTPUT}" | grep -q '"status": *"ok"'     || { echo "FAIL: /health did not report ok"; exit 1; }
echo "${OUTPUT}" | grep -q '"status": *"ready"'  || { echo "FAIL: /ready did not report ready"; exit 1; }
echo "${OUTPUT}" | grep -q 'dashboard HTTP 200'  || { echo "FAIL: dashboard did not return 200"; exit 1; }

if [[ -n "${EXPECT_VERSION}" ]]; then
  if echo "${OUTPUT}" | grep -q "\"version\": *\"${EXPECT_VERSION}\""; then
    log "Version ${EXPECT_VERSION} confirmed live on ${SERVICE}"
  else
    echo "FAIL: expected version ${EXPECT_VERSION} was not served by ${SERVICE}" >&2
    exit 1
  fi
fi

log "Smoke test PASSED"
