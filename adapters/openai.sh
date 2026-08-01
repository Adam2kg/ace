#!/usr/bin/env bash
# openai.sh — standalone OpenAI (different-family "second opinion") adapter.
# =============================================================================
# ZERO octopus dependencies. Harvested from claude-octopus/scripts/helpers/
# openai-compatible-agent.py (copied alongside this file) + SPEC §2.3.
#
# CONTRACT (the hard-won knowledge):
#  - The value of this seat is DECORRELATED ERROR: a different training family
#    than Claude. That is the only reason it exists.
#  - Do NOT build on the codex CLI: it is quota-dead (exit 137), and exit 137
#    never matched octopus's quota-watcher stderr patterns -> a silent zombie.
#    Use the API-key path instead.
#  - --health uses GET /v1/models: it validates the key AND returns the exact
#    model IDs this account can use — no model-guessing, one cheap call. This is
#    the "OpenAI API-key path" validation spike the spec left owed (§6 Decision 2).
#  - Default run is a one-shot chat completion (what a second opinion needs).
#    --agent routes to the harvested stdlib-only agentic loop (tools + retries on
#    429/502/503/504) for when you want it to actually edit code.
#  - Set OPENAI_MODEL to a chat model your key can access (confirm via --health).
#
# Usage:
#   openai.sh "<prompt>"        one-shot second opinion (argv)
#   openai.sh                   prompt on stdin
#   openai.sh --health          validate key + list available model IDs
#   openai.sh --agent "<task>"  full agentic loop (edits files under cwd)
# Env:
#   OPENAI_API_KEY (or set OPENAI_KEY_ENV to another var name),
#   OPENAI_BASE_URL=https://api.openai.com/v1, OPENAI_MODEL, OPENAI_TIMEOUT=60
# =============================================================================
set -uo pipefail

OPENAI_BASE_URL="${OPENAI_BASE_URL:-https://api.openai.com/v1}"
OPENAI_MODEL="${OPENAI_MODEL:-gpt-5}"            # verified available on this account 2026-07-24 (also: gpt-5-chat-latest, gpt-5-mini, gpt-4.1, gpt-4o)
OPENAI_KEY_ENV="${OPENAI_KEY_ENV:-OPENAI_API_KEY}"
OPENAI_TIMEOUT="${OPENAI_TIMEOUT:-60}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"

# indirect fetch of the key from whatever var name OPENAI_KEY_ENV points at
_KEY=""
eval "_KEY=\${$OPENAI_KEY_ENV:-}"

_need() { command -v "$1" >/dev/null 2>&1 || { echo "openai: '$1' required" >&2; exit 69; }; }

_oneshot() {
  local prompt="$1" body resp
  [ -n "$_KEY" ] || { echo "openai: \$$OPENAI_KEY_ENV not set" >&2; return 2; }
  body="$(jq -n --arg m "$OPENAI_MODEL" --arg p "$prompt" \
    '{model:$m, messages:[{role:"user",content:$p}], temperature:0}')"
  resp="$(curl -sf --max-time "$OPENAI_TIMEOUT" "$OPENAI_BASE_URL/chat/completions" \
    -H "Authorization: Bearer $_KEY" -H 'Content-Type: application/json' -d "$body" 2>/dev/null)"
  [ -n "$resp" ] || { echo "openai: request failed (network / key / quota / model '$OPENAI_MODEL')" >&2; return 1; }
  local text; text="$(printf '%s' "$resp" | jq -r '.choices[0].message.content // empty' 2>/dev/null)"
  [ -n "$text" ] || { echo "openai: no content in response" >&2; return 1; }
  printf '%s\n' "$text"
}

health() {
  _need curl; _need jq
  [ -n "$_KEY" ] || { echo "openai: \$$OPENAI_KEY_ENV not set" >&2; return 2; }
  # Status-aware probe: a 500 (server error) must NOT be reported as a dead key.
  # This distinction is the zombie-gate lesson applied to our own health check.
  local bodyf http; bodyf="$(mktemp)"
  http="$(curl -s -o "$bodyf" -w '%{http_code}' --max-time "$OPENAI_TIMEOUT" \
    "$OPENAI_BASE_URL/models" -H "Authorization: Bearer $_KEY" 2>/dev/null)"
  case "$http" in
    200)
      local n; n="$(jq -r '.data | length' "$bodyf" 2>/dev/null || echo 0)"
      rm -f "$bodyf"
      [ "${n:-0}" -gt 0 ] 2>/dev/null || { echo "openai: UNAVAILABLE — 200 but no models" >&2; return 1; }
      echo "OPENAI-OK (key valid; $n models available)"
      printf ''  # model IDs printed by caller if wanted
      return 0 ;;
    401|403) rm -f "$bodyf"; echo "openai: KEY DEAD (HTTP $http) — rotate/replace the key" >&2; return 1 ;;
    429)     rm -f "$bodyf"; echo "openai: RATE-LIMITED / quota (HTTP 429) — key is valid, retry later" >&2; return 3 ;;
    5*)      rm -f "$bodyf"; echo "openai: OPENAI SERVER ERROR (HTTP $http) — key not disproven; transient, retry later" >&2; return 4 ;;
    000|"")  rm -f "$bodyf"; echo "openai: NETWORK unreachable (no HTTP status)" >&2; return 5 ;;
    *)       rm -f "$bodyf"; echo "openai: UNAVAILABLE (HTTP $http)" >&2; return 1 ;;
  esac
}

main() {
  case "${1:-}" in
    --health|--probe) health ;;
    --agent) shift; _need python3
             python3 "$HERE/openai-compatible-agent.py" --cwd "$PWD" \
               --base-url "$OPENAI_BASE_URL" --api-key-env "$OPENAI_KEY_ENV" \
               --model "$OPENAI_MODEL" ${1:+--prompt "$1"} ;;
    "" ) _need curl; _need jq; _oneshot "$(cat)" ;;
    * ) _need curl; _need jq; _oneshot "$1" ;;
  esac
}
main "$@"
