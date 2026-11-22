#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# codespaces-urls.sh — print the public URLs to paste into your submission,
# and check which ones actually answer.
#
#   bash scripts/codespaces-urls.sh
#
# A port only answers from the public internet after you set it to Public:
#   PORTS tab -> right-click the port -> Port Visibility -> Public
# ---------------------------------------------------------------------------
set -uo pipefail

NAME="${CODESPACE_NAME:-}"
DOMAIN="${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN:-app.github.dev}"

if [[ -z "$NAME" ]]; then
  echo "Not running inside a Codespace (CODESPACE_NAME is unset)."
  echo "Local equivalents: http://localhost:<port>"
  NAME="localhost"
fi

url() {
  if [[ "$NAME" == "localhost" ]]; then echo "http://localhost:$1"
  else echo "https://${NAME}-$1.${DOMAIN}"; fi
}

row() {
  local port="$1" label="$2" path="${3:-/version}"
  local u; u="$(url "$port")"
  local code; code="$(curl -fsS -o /dev/null -w '%{http_code}' --max-time 6 \
                      "http://localhost:${port}${path}" 2>/dev/null)"
  [[ -z "$code" || "$code" == "000" ]] && code="down"
  printf '  %-22s %-6s %-5s %s\n' "$label" "$port" "$code" "${u}${path}"
}

echo
echo "  Codespace: ${NAME}"
echo "  (the 'code' column is the response from inside the Codespace;"
echo "   a port must be set to Public before the URL works for your assessor)"
echo
printf '  %-22s %-6s %-5s %s\n' "WHAT" "PORT" "CODE" "URL"
printf '  %s\n' "------------------------------------------------------------------------"
row 8080  "Jenkins"            "/login"
row 30080 "App dashboard"      "/"
row 30080 "App version"        "/version"
row 30081 "Blue-green ACTIVE"
row 30082 "Blue preview"
row 30083 "Green preview"
row 30084 "Canary direct"
row 30085 "A/B variant A"
row 30086 "A/B variant B"
row 30090 "Ingress"
echo

if curl -fsS --max-time 6 http://localhost:30090/version >/dev/null 2>&1; then
  echo "  A/B routing check through the ingress:"
  printf '    control        : %s\n' "$(curl -fsS --max-time 6 http://localhost:30090/version | tr -d '\n')"
  printf '    X-Variant: B   : %s\n' "$(curl -fsS --max-time 6 -H 'X-Variant: B' http://localhost:30090/version | tr -d '\n')"
  echo
fi

cat <<'NOTE'
  Paste into your submission:
    * the public URL for each endpoint above
    * a note that the cluster is k3d running in a GitHub Codespace, so the
      URLs are live only while the Codespace is running
    * the terminal transcripts, which are valid evidence regardless
NOTE
