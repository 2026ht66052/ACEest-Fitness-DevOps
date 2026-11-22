#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# deploy.sh — apply one of the five progressive delivery strategies.
#
# Usage:
#   ./scripts/deploy.sh --strategy rolling      --image user/aceest-fitness:3.2.4 --version 3.2.4
#   ./scripts/deploy.sh --strategy blue-green   --image ... --version ... [--promote]
#   ./scripts/deploy.sh --strategy canary       --image ... --version ... [--weight 20] [--promote]
#   ./scripts/deploy.sh --strategy shadow       --image ... --version ...
#   ./scripts/deploy.sh --strategy ab-testing   --image ... --version ...
#
# Every strategy records a change-cause annotation so that
# `kubectl rollout history` and `scripts/rollback.sh` have something to work
# with.
# ---------------------------------------------------------------------------
set -euo pipefail

STRATEGY=""
IMAGE=""
VERSION=""
NAMESPACE="aceest"
PROMOTE="false"
WEIGHT=""
TIMEOUT="300s"

usage() { sed -n '2,20p' "$0"; exit 1; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --strategy)  STRATEGY="$2"; shift 2 ;;
    --image)     IMAGE="$2"; shift 2 ;;
    --version)   VERSION="$2"; shift 2 ;;
    --namespace) NAMESPACE="$2"; shift 2 ;;
    --weight)    WEIGHT="$2"; shift 2 ;;
    --promote)   PROMOTE="true"; shift ;;
    -h|--help)   usage ;;
    *) echo "Unknown argument: $1" >&2; usage ;;
  esac
done

[[ -n "$STRATEGY" && -n "$IMAGE" && -n "$VERSION" ]] || usage

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
K="kubectl -n ${NAMESPACE}"
CAUSE="image=${IMAGE} version=${VERSION} strategy=${STRATEGY} at $(date -u +%FT%TZ)"

log() { printf '\n\033[1;33m==> %s\033[0m\n' "$*"; }

# In a Codespace the ingress rules must be host-less, because GitHub's
# port-forwarding proxy rewrites the Host header. k8s/codespaces/ holds those
# variants; everywhere else we use the host-based manifests.
apply_ingress() {
  local kind="$1"
  if [[ -n "${CODESPACES:-}" ]]; then
    log "Applying the Codespaces (host-less) ${kind} ingress"
    # Only one canary-style pair can own "/" at a time, so clear the other.
    ${K} delete ingress aceest-fitness-canary aceest-fitness-ab-variant-b \
         --ignore-not-found >/dev/null 2>&1 || true
    ${K} apply -f "${ROOT}/k8s/codespaces/ingress-${kind}.yaml"
  else
    case "$kind" in
      canary) ${K} apply -f "${ROOT}/k8s/canary/ingress-canary.yaml" ;;
      ab)     ${K} apply -f "${ROOT}/k8s/ab-testing/ingress-ab.yaml" ;;
      shadow) : ;;  # the mirror ingress ships inside deployment-shadow.yaml
    esac
  fi
}

# ---------------------------------------------------------------------------
log "Ensuring namespace and shared resources exist"
kubectl apply -f "${ROOT}/k8s/base/namespace.yaml"
${K} apply -f "${ROOT}/k8s/base/config.yaml"
${K} apply -f "${ROOT}/k8s/base/service.yaml"

wait_rollout() {
  local deploy="$1"
  log "Waiting for ${deploy} to become available"
  ${K} rollout status "deploy/${deploy}" --timeout="${TIMEOUT}"
}

# ---------------------------------------------------------------------------
case "$STRATEGY" in

  # ---------------------------- ROLLING UPDATE ----------------------------
  rolling)
    log "ROLLING UPDATE -> ${IMAGE}"
    ${K} apply -f "${ROOT}/k8s/rolling/deployment.yaml"
    ${K} set image deploy/aceest-fitness "app=${IMAGE}" --record=false
    ${K} set env  deploy/aceest-fitness "APP_VERSION=${VERSION}" "APP_TRACK=stable"
    ${K} annotate deploy/aceest-fitness "kubernetes.io/change-cause=${CAUSE}" --overwrite
    wait_rollout aceest-fitness
    ${K} rollout history deploy/aceest-fitness
    ;;

  # ------------------------------ BLUE-GREEN ------------------------------
  blue-green)
    ${K} apply -f "${ROOT}/k8s/blue-green/"

    ACTIVE=$(${K} get svc aceest-fitness-active -o jsonpath='{.spec.selector.color}')
    IDLE=$([[ "$ACTIVE" == "blue" ]] && echo green || echo blue)
    log "Active colour is ${ACTIVE}; deploying ${VERSION} to the idle colour: ${IDLE}"

    ${K} set image "deploy/aceest-fitness-${IDLE}" "app=${IMAGE}"
    ${K} set env   "deploy/aceest-fitness-${IDLE}" "APP_VERSION=${VERSION}" "APP_TRACK=${IDLE}"
    ${K} annotate  "deploy/aceest-fitness-${IDLE}" "kubernetes.io/change-cause=${CAUSE}" --overwrite
    wait_rollout "aceest-fitness-${IDLE}"

    log "Smoke testing the idle colour through its preview service"
    "${ROOT}/scripts/smoke-test.sh" --namespace "${NAMESPACE}" \
        --service "aceest-fitness-${IDLE}-preview" --expect-version "${VERSION}"

    if [[ "$PROMOTE" == "true" ]]; then
      log "PROMOTING ${IDLE} — switching 100% of traffic"
      ${K} patch svc aceest-fitness-active \
        -p "{\"spec\":{\"selector\":{\"app\":\"aceest-fitness\",\"color\":\"${IDLE}\"}}}"
      ${K} annotate svc aceest-fitness-active \
        "aceest.io/active-color=${IDLE}" \
        "aceest.io/previous-color=${ACTIVE}" --overwrite
      log "Traffic now served by ${IDLE}. Rollback: ./scripts/rollback.sh --strategy blue-green"
    else
      log "${IDLE} is live but NOT receiving traffic. Re-run with --promote to cut over."
    fi
    ;;

  # -------------------------------- CANARY --------------------------------
  canary)
    ${K} apply -f "${ROOT}/k8s/rolling/deployment.yaml"
    ${K} apply -f "${ROOT}/k8s/canary/deployment-canary.yaml"

    log "Deploying canary ${VERSION}"
    ${K} set image deploy/aceest-fitness-canary "app=${IMAGE}"
    ${K} set env   deploy/aceest-fitness-canary "APP_VERSION=${VERSION}" "APP_TRACK=canary"
    ${K} annotate  deploy/aceest-fitness-canary "kubernetes.io/change-cause=${CAUSE}" --overwrite
    ${K} scale deploy/aceest-fitness-canary --replicas=1
    wait_rollout aceest-fitness-canary
    apply_ingress canary

    "${ROOT}/scripts/smoke-test.sh" --namespace "${NAMESPACE}" \
        --service aceest-fitness-canary --expect-version "${VERSION}"

    if [[ -n "$WEIGHT" ]]; then
      "${ROOT}/scripts/canary-weight.sh" "${WEIGHT}" "${NAMESPACE}"
    fi

    if [[ "$PROMOTE" == "true" ]]; then
      log "PROMOTING canary: rolling the stable deployment onto ${IMAGE}"
      ${K} set image deploy/aceest-fitness "app=${IMAGE}"
      ${K} set env   deploy/aceest-fitness "APP_VERSION=${VERSION}"
      wait_rollout aceest-fitness
      ${K} scale deploy/aceest-fitness-canary --replicas=0
      log "Canary promoted and scaled down."
    else
      STABLE=$(${K} get deploy aceest-fitness -o jsonpath='{.spec.replicas}')
      CANARY=$(${K} get deploy aceest-fitness-canary -o jsonpath='{.spec.replicas}')
      log "Canary live at ~$((100 * CANARY / (STABLE + CANARY)))% of traffic (stable=${STABLE}, canary=${CANARY})"
    fi
    ;;

  # -------------------------------- SHADOW --------------------------------
  shadow)
    ${K} apply -f "${ROOT}/k8s/rolling/deployment.yaml"
    ${K} apply -f "${ROOT}/k8s/shadow/deployment-shadow.yaml"
    apply_ingress shadow

    log "Deploying SHADOW ${VERSION} (receives mirrored traffic only)"
    ${K} set image deploy/aceest-fitness-shadow "app=${IMAGE}"
    ${K} set env   deploy/aceest-fitness-shadow "APP_VERSION=${VERSION}" "APP_TRACK=shadow"
    ${K} annotate  deploy/aceest-fitness-shadow "kubernetes.io/change-cause=${CAUSE}" --overwrite
    wait_rollout aceest-fitness-shadow

    if ${K} get crd virtualservices.networking.istio.io >/dev/null 2>&1; then
      log "Istio detected — applying VirtualService mirroring"
      ${K} apply -f "${ROOT}/k8s/shadow/shadow-istio.yaml"
    else
      log "Istio not installed — using the NGINX ingress mirror-target annotation"
    fi

    log "Shadow is live. Inspect it with:  kubectl -n ${NAMESPACE} logs -l track=shadow -f"
    ;;

  # ------------------------------ A/B TESTING -----------------------------
  ab-testing)
    ${K} apply -f "${ROOT}/k8s/ab-testing/ab-deployments.yaml"
    apply_ingress ab

    log "Deploying variant B as ${VERSION} (variant A remains the control)"
    ${K} set image deploy/aceest-fitness-variant-b "app=${IMAGE}"
    ${K} set env   deploy/aceest-fitness-variant-b "APP_VERSION=${VERSION}" "APP_TRACK=variant-b"
    ${K} annotate  deploy/aceest-fitness-variant-b "kubernetes.io/change-cause=${CAUSE}" --overwrite
    wait_rollout aceest-fitness-variant-a
    wait_rollout aceest-fitness-variant-b

    "${ROOT}/scripts/smoke-test.sh" --namespace "${NAMESPACE}" \
        --service aceest-fitness-variant-b --expect-version "${VERSION}"

    log "A/B live. Variant B is selected with the header  X-Variant: B"
    ;;

  *)
    echo "Unknown strategy: ${STRATEGY}" >&2
    exit 2
    ;;
esac

log "Deployment summary"
${K} get deploy,svc,pods -l app=aceest-fitness -o wide
