#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Runs once, automatically, when the Codespace is created.
# Installs k3d, builds the Python venv, and creates the Kubernetes cluster.
# Safe to re-run by hand:  bash .devcontainer/post-create.sh
# ---------------------------------------------------------------------------
set -euo pipefail

log() { printf '\n\033[1;33m==> %s\033[0m\n' "$*"; }

log "Installing k3d (Kubernetes in Docker)"
if ! command -v k3d >/dev/null 2>&1; then
  curl -s https://raw.githubusercontent.com/k3d-io/k3d/main/install.sh | bash
fi
k3d version

log "Creating the Python virtual environment"
python3 -m venv .venv
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet -r requirements-dev.txt
.venv/bin/python -m pytest -q --no-header -p no:cacheprovider 2>&1 | tail -3 || true

log "Making the helper scripts executable"
chmod +x scripts/*.sh .devcontainer/*.sh || true

log "Creating the k3d cluster"
bash scripts/codespaces-setup.sh

cat <<'BANNER'

  ┌──────────────────────────────────────────────────────────────────────┐
  │  ACEest Fitness DevOps lab is ready.                                 │
  │                                                                      │
  │  Next steps:                                                         │
  │    1.  bash scripts/codespaces-jenkins.sh      # start Jenkins       │
  │    2.  open the PORTS tab, right-click 8080 -> Open in Browser        │
  │    3.  docker login                            # your Docker Hub     │
  │    4.  make deploy STRATEGY=rolling                                  │
  │                                                                      │
  │  Full walkthrough:  docs/NO_DOCKER_GUIDE.md                          │
  └──────────────────────────────────────────────────────────────────────┘

BANNER
