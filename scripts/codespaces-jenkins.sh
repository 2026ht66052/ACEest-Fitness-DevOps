#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# codespaces-jenkins.sh — run Jenkins inside the Codespace.
#
#   bash scripts/codespaces-jenkins.sh            # start (prints the password)
#   bash scripts/codespaces-jenkins.sh --stop
#   bash scripts/codespaces-jenkins.sh --logs
#
# Jenkins runs from its WAR on the Codespace's own JVM rather than in a
# container. That is deliberate: Jenkins then inherits the environment's
# docker, kubectl, k3d and python binaries directly, so there is no Docker
# socket to mount and — the part that usually costs an afternoon — no
# kubeconfig rewriting, because the k3d kubeconfig already works here.
#
# JENKINS_HOME lives in $HOME, which survives stopping and restarting the
# Codespace. Deleting the Codespace destroys it, so capture your screenshots
# as you go.
# ---------------------------------------------------------------------------
set -euo pipefail

JENKINS_HOME="${JENKINS_HOME:-$HOME/jenkins_home}"
JENKINS_WAR="${JENKINS_WAR:-$HOME/jenkins.war}"
JENKINS_PORT="${JENKINS_PORT:-8080}"
PID_FILE="$HOME/.jenkins.pid"
LOG_FILE="$HOME/jenkins.log"

log() { printf '\n\033[1;33m==> %s\033[0m\n' "$*"; }

case "${1:-start}" in
  --stop)
    if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
      kill "$(cat "$PID_FILE")" && rm -f "$PID_FILE"
      log "Jenkins stopped"
    else
      log "Jenkins is not running"
    fi
    exit 0
    ;;
  --logs)
    tail -f "$LOG_FILE"
    ;;
esac

if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  log "Jenkins is already running on port ${JENKINS_PORT} (pid $(cat "$PID_FILE"))"
  exit 0
fi

if [[ ! -f "$JENKINS_WAR" ]]; then
  log "Downloading the latest Jenkins LTS WAR"
  curl -fsSL -o "$JENKINS_WAR" \
    "https://get.jenkins.io/war-stable/latest/jenkins.war"
fi

mkdir -p "$JENKINS_HOME"

log "Starting Jenkins on port ${JENKINS_PORT}"
JENKINS_HOME="$JENKINS_HOME" nohup java \
  -Djava.awt.headless=true \
  -Djenkins.install.runSetupWizard=true \
  -jar "$JENKINS_WAR" \
  --httpPort="${JENKINS_PORT}" \
  > "$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"

log "Waiting for Jenkins to come up (this takes 30-60 seconds the first time)"
for _ in $(seq 1 60); do
  if curl -fsS "http://localhost:${JENKINS_PORT}/login" >/dev/null 2>&1; then
    break
  fi
  sleep 3
done

SECRET="$JENKINS_HOME/secrets/initialAdminPassword"
cat <<BANNER

  ┌──────────────────────────────────────────────────────────────────────┐
  │  Jenkins is running.                                                 │
  │                                                                      │
  │  Open it:  PORTS tab -> port ${JENKINS_PORT} -> Open in Browser                │
  │  Logs:     bash scripts/codespaces-jenkins.sh --logs                 │
  │  Stop:     bash scripts/codespaces-jenkins.sh --stop                 │
  └──────────────────────────────────────────────────────────────────────┘

BANNER

if [[ -f "$SECRET" ]]; then
  echo "  Initial admin password:"
  echo
  echo "      $(cat "$SECRET")"
  echo
else
  echo "  (Setup already completed — use the account you created.)"
  echo
fi

log "Tool availability inside Jenkins' environment"
printf '    docker  : %s\n' "$(docker --version 2>/dev/null || echo MISSING)"
printf '    kubectl : %s\n' "$(kubectl version --client -o yaml 2>/dev/null | grep gitVersion | head -1 | awk '{print $2}' || echo MISSING)"
printf '    python3 : %s\n' "$(python3 -V 2>/dev/null || echo MISSING)"
printf '    java    : %s\n' "$(java -version 2>&1 | head -1)"
