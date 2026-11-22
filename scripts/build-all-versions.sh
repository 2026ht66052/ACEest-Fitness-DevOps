#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# build-all-versions.sh — build, tag and push every application version so the
# Docker Hub repository shows the full version history required by the
# assignment ("your own docker image repo with all versions").
#
#   export DOCKERHUB_USER=yourname
#   docker login
#   ./scripts/build-all-versions.sh            # build + push every version
#   ./scripts/build-all-versions.sh --no-push  # build locally only
#
# Each version corresponds to a git tag (see docs/GIT_WORKFLOW.md); the script
# checks the tag out, builds from that source and restores your branch.
# ---------------------------------------------------------------------------
set -euo pipefail

: "${DOCKERHUB_USER:?Set DOCKERHUB_USER to your Docker Hub username}"
IMAGE="${DOCKERHUB_USER}/aceest-fitness"
PUSH="true"
[[ "${1:-}" == "--no-push" ]] && PUSH="false"

VERSIONS=(1.0 1.1 1.1.2 2.0.1 2.1.2 2.2.1 2.2.4 3.0.1 3.1.2 3.2.4)

BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo main)"
restore() { git checkout --quiet "${BRANCH}" 2>/dev/null || true; }
trap restore EXIT

for VERSION in "${VERSIONS[@]}"; do
  printf '\n\033[1;33m==> Building %s:%s\033[0m\n' "${IMAGE}" "${VERSION}"

  if git rev-parse --verify --quiet "refs/tags/v${VERSION}" >/dev/null; then
    git checkout --quiet "v${VERSION}"
  else
    echo "    (tag v${VERSION} not found — building from the current tree)"
  fi

  docker build \
    --build-arg "APP_VERSION=${VERSION}" \
    --build-arg "GIT_COMMIT=$(git rev-parse --short HEAD)" \
    --build-arg "BUILD_DATE=$(date -u +%FT%TZ)" \
    -t "${IMAGE}:${VERSION}" .

  if [[ "${PUSH}" == "true" ]]; then
    docker push "${IMAGE}:${VERSION}"
  fi

  git checkout --quiet "${BRANCH}"
done

# The newest version also becomes :latest
docker tag "${IMAGE}:${VERSIONS[-1]}" "${IMAGE}:latest"
[[ "${PUSH}" == "true" ]] && docker push "${IMAGE}:latest"

printf '\n\033[1;32m==> Done. Tags in %s:\033[0m\n' "${IMAGE}"
docker images "${IMAGE}" --format '  {{.Tag}}\t{{.Size}}\t{{.CreatedSince}}'
