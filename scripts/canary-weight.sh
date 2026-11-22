#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# canary-weight.sh — shift the canary traffic share.
#
#   ./scripts/canary-weight.sh 20          # ~20% of traffic to the canary
#   ./scripts/canary-weight.sh 50 aceest
#
# Works two ways at once:
#   * replica ratio on the shared service (always applies)
#   * nginx canary-weight annotation (when the canary ingress exists)
# ---------------------------------------------------------------------------
set -euo pipefail

WEIGHT="${1:-10}"
NAMESPACE="${2:-aceest}"
TOTAL_REPLICAS="${TOTAL_REPLICAS:-10}"

if ! [[ "$WEIGHT" =~ ^[0-9]+$ ]] || (( WEIGHT > 100 )); then
  echo "Weight must be an integer between 0 and 100" >&2
  exit 1
fi

K="kubectl -n ${NAMESPACE}"

CANARY=$(( TOTAL_REPLICAS * WEIGHT / 100 ))
STABLE=$(( TOTAL_REPLICAS - CANARY ))
(( WEIGHT > 0 && CANARY == 0 )) && { CANARY=1; STABLE=$(( TOTAL_REPLICAS - 1 )); }

printf '\n\033[1;33m==> Setting canary share to ~%s%% (stable=%s, canary=%s)\033[0m\n' \
  "$WEIGHT" "$STABLE" "$CANARY"

${K} scale deploy/aceest-fitness        --replicas="${STABLE}"
${K} scale deploy/aceest-fitness-canary --replicas="${CANARY}"
${K} rollout status deploy/aceest-fitness-canary --timeout=180s

if ${K} get ingress aceest-fitness-canary >/dev/null 2>&1; then
  ${K} annotate ingress aceest-fitness-canary \
    "nginx.ingress.kubernetes.io/canary-weight=${WEIGHT}" --overwrite
  echo "Ingress canary-weight set to ${WEIGHT}"
fi

${K} get deploy -l app=aceest-fitness
