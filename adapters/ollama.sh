#!/usr/bin/env bash
# ollama.sh — standalone local Ollama provider adapter.
# =============================================================================
# ZERO octopus dependencies. Harvested from claude-octopus/scripts/helpers/
# ollama-run.sh + ollama-pull-guard.lib.sh + config/providers/ollama + SPEC §2.2.
#
# CONTRACT (the hard-won knowledge):
#  - FAIL CLOSED on an absent model. `ollama run <model>` SILENTLY auto-pulls a
#    missing model; a provider-failure cascade once kicked off a ~42 GB download
#    with no human in the loop. This adapter NEVER runs a model it has not first
#    confirmed present via /api/tags — it tells you to pre-pull instead.
#  - Use the HTTP API (POST /api/generate), not the CLI, for clean status/parse.
#  - think:false + temperature:0 + capped num_predict. A "thinking" model can
#    spend its whole token budget narrating reasoning and return an EMPTY
#    response — the zombie failure. Empty response is treated as FAILURE.
#  - Routing: code -> qwen2.5-coder:7b, bulk classify/extract -> qwen3:4b.
#    Nothing to qwen3:8b (dominated on this CPU-only box). gpt-oss:120b-cloud is
#    CLOUD, not local — never route GDPR/PII data to it.
#
# Usage:
#   ollama.sh "<prompt>" [model]      run (model defaults to $OLLAMA_MODEL)
#   ollama.sh                         prompt on stdin
#   ollama.sh --health [model]        liveness + end-to-end non-empty generate
# Env:
#   OLLAMA_URL=http://localhost:11434, OLLAMA_MODEL=qwen2.5-coder:7b,
#   OLLAMA_NUM_PREDICT=512, OLLAMA_TIMEOUT=120
# =============================================================================
set -uo pipefail

OLLAMA_URL="${OLLAMA_URL:-http://localhost:11434}"
OLLAMA_MODEL="${OLLAMA_MODEL:-qwen2.5-coder:7b}"
OLLAMA_NUM_PREDICT="${OLLAMA_NUM_PREDICT:-512}"
OLLAMA_TIMEOUT="${OLLAMA_TIMEOUT:-120}"

_need() { command -v "$1" >/dev/null 2>&1 || { echo "ollama: '$1' required" >&2; exit 69; }; }

# 0 = present, 2 = server unreachable, 1 = reachable but model absent
_present() {
  local model="$1" tags
  tags="$(curl -sf --max-time 3 "$OLLAMA_URL/api/tags" 2>/dev/null || true)"
  [ -n "$tags" ] || return 2
  printf '%s' "$tags" | jq -e --arg m "$model" \
    '[.models[]?.name | select(. == $m or . == ($m + ":latest") or (split(":")[0] == $m))] | length > 0' \
    >/dev/null 2>&1 && return 0
  return 1
}

_generate() {
  local prompt="$1" model="$2" npredict="${3:-$OLLAMA_NUM_PREDICT}" body
  body="$(jq -n --arg m "$model" --arg p "$prompt" --argjson n "$npredict" \
    '{model:$m, prompt:$p, stream:false, think:false, options:{temperature:0, num_predict:$n}}')"
  curl -sf --max-time "$OLLAMA_TIMEOUT" "$OLLAMA_URL/api/generate" \
    -H 'Content-Type: application/json' -d "$body" 2>/dev/null
}

run() {
  _need curl; _need jq
  local prompt="$1" model="${2:-$OLLAMA_MODEL}"
  _present "$model"; local rc=$?
  if [ "$rc" -eq 2 ]; then echo "ollama: server unreachable at $OLLAMA_URL (start it: ollama serve)" >&2; return 69; fi
  if [ "$rc" -eq 1 ]; then echo "ollama: model '$model' not present — FAIL CLOSED (no auto-pull). Pre-pull:  ollama pull $model" >&2; return 70; fi
  local resp text
  resp="$(_generate "$prompt" "$model")"
  text="$(printf '%s' "$resp" | jq -r '.response // empty' 2>/dev/null)"
  [ -n "$text" ] || { echo "ollama: EMPTY response from '$model' (thinking may have consumed the budget)" >&2; return 1; }
  printf '%s\n' "$text"
}

health() {
  _need curl; _need jq
  local model="${1:-$OLLAMA_MODEL}"
  _present "$model"; local rc=$?
  [ "$rc" -eq 2 ] && { echo "ollama: server unreachable at $OLLAMA_URL" >&2; return 69; }
  [ "$rc" -eq 1 ] && { echo "ollama: model '$model' absent (pre-pull: ollama pull $model)" >&2; return 1; }
  # end-to-end tiny generate; non-empty response is the zombie-safe aliveness proof
  local resp text
  resp="$(_generate 'Reply with exactly: OLLAMA-OK' "$model" 16)"
  text="$(printf '%s' "$resp" | jq -r '.response // empty' 2>/dev/null)"
  [ -n "$text" ] || { echo "ollama: EMPTY response (thinking consumed budget?)" >&2; return 1; }
  case "$text" in
    *OLLAMA-OK*) echo "OLLAMA-OK ($model)" ;;
    *)           echo "OLLAMA-OK ($model; alive, sentinel drift: $(printf '%s' "$text" | tr -d '\n' | cut -c1-40))" ;;
  esac
  return 0
}

main() {
  case "${1:-}" in
    --health|--probe) shift; health "${1:-}" ;;
    "" ) run "$(cat)" ;;
    * ) run "$@" ;;
  esac
}
main "$@"
