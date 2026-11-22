#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# rollback.sh — revert to the last stable version.
#
#   ./scripts/rollback.sh --strategy rolling      # kubectl rollout undo
#   ./scripts/rollback.sh --strategy blue-green   # flip the service selector back
#   ./scripts/rollback.sh --strategy canary       # scale the canary to zero
#   ./scripts/rollback.sh --strategy shadow       # delete the shadow deployment
#   ./scripts/rollback.sh --strategy ab-testing   # send all traffic to variant A
#   ./scripts/rollback.sh --strategy rolling --to-revision 3
#
# This is the script the Jenkins `post { failure { ... } }` block invokes, so a
# failed deployment never leaves a broken version serving traffic.
# ---------------------------------------------------------------------------
set -euo pipefail

STRATEGY="rolling"
NAMESPACE="aceest"
REVISION=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --strategy)     STRATEGY="$2"; shift 2 ;;
    --namespace)    NAMESPACE="$2"; shift 2 ;;
    --to-revision)  REVISION="$2"; shift 2 ;;
    -h|--help)      sed -n '2,18p' "$0"; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done

K="kubectl -n ${NAMESPACE}"
log() { printf '\n\033[1;31m==> ROLLBACK: %s\033[0m\n' "$*"; }

case "$STRATEGY" in

  rolling)
    log "Reverting deploy/aceest-fitness"
    ${K} rollout history deploy/aceest-fitness || true
    if [[ -n "$REVISION" ]]; then
      ${K} rollout undo deploy/aceest-fitness --to-revision="${REVISION}"
    else
      ${K} rollout undo deploy/aceest-fitness
    fi
    ${K} rollout status deploy/aceest-fitness --timeout=300s
    ;;

  blue-green)
    CURRENT=$(${K} get svc aceest-fitness-active -o jsonpath='{.spec.selector.color}')
    PREVIOUS=$(${K} get svc aceest-fitness-active \
                 -o jsonpath='{.metadata.annotations.aceest\.io/previous-color}' 2>/dev/null || true)
    [[ -n "$PREVIOUS" ]] || PREVIOUS=$([[ "$CURRENT" == "blue" ]] && echo green || echo blue)

    log "Switching traffic from ${CURRENT} back to ${PREVIOUS}"
    ${K} patch svc aceest-fitness-active \
      -p "{\"spec\":{\"selector\":{\"app\":\"aceest-fitness\",\"color\":\"${PREVIOUS}\"}}}"
    ${K} annotate svc aceest-fitness-active \
      "aceest.io/active-color=${PREVIOUS}" "aceest.io/previous-color=${CURRENT}" --overwrite
    ${K} get svc aceest-fitness-active -o jsonpath='{.spec.selector}'; echo
    ;;

  canary)
    log "Scaling the canary to zero — 100% of traffic returns to stable"
    ${K} scale deploy/aceest-fitness-canary --replicas=0
    if ${K} get ingress aceest-fitness-canary >/dev/null 2>&1; then
      ${K} annotate ingress aceest-fitness-canary \
        nginx.ingress.kubernetes.io/canary-weight="0" --overwrite
    fi
    ${K} get deploy -l app=aceest-fitness
    ;;

  shadow)
    log "Removing the shadow deployment (no user traffic was ever affected)"
    ${K} delete deploy aceest-fitness-shadow --ignore-not-found
    ${K} delete ingress aceest-fitness-mirror --ignore-not-found
    ;;

  ab-testing)
    log "Ending the experiment — all traffic to variant A (control)"
    ${K} delete ingress aceest-fitness-ab-variant-b --ignore-not-found
    ${K} scale deploy/aceest-fitness-variant-b --replicas=0
    ;;

  *)
    echo "Unknown strategy: ${STRATEGY}" >&2
    exit 2
    ;;
esac

log "Post-rollback state"
${K} get deploy,svc,pods -l app=aceest-fitness
