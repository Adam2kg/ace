#!/usr/bin/env bash
# agy.sh — standalone Antigravity (Gemini-family) provider adapter.
# =============================================================================
# ZERO octopus dependencies. Harvested from claude-octopus/scripts/helpers/
# agy-exec.sh + config/providers/agy/CLAUDE.md + ACE-migration SPEC §2.1.
#
# CONTRACT (the hard-won knowledge):
#  - agy runs Gemini-family models, authed via Google OAuth (state in
#    ~/.gemini/antigravity-cli/ — OUTSIDE octopus, survives its deletion).
#  - DO NOT pass --model. The old octopus default ("Claude Sonnet ... Thinking")
#    forced agy onto an exhaustible Claude/GPT quota group -> silent EMPTY output.
#    Omitting --model uses the model picked in agy's own /model UI (Gemini Flash).
#  - Two input forms exist across versions:
#      argv  : agy -p "<prompt>" ...           (SPEC-recommended; 1.1.6+)
#      stdin : printf %s "<prompt>" | agy --print ...   (what octopus used on 1.1.4)
#    This adapter defaults to argv and FALLS BACK to stdin; --health reports which
#    actually works on this box, resolving the spec's owed argv-vs-stdin spike.
#  - No `timeout` binary on macOS: bounded-exec is done in-process (_bounded).
#  - agy print mode emits nothing from a backgrounded job in some setups; the
#    health probe runs it foreground under a wall-clock bound.
#
# Usage:
#   agy.sh "<prompt>"        prompt as argv
#   agy.sh                   prompt on stdin
#   agy.sh --health          zombie-safe sentinel; prints AGY-OK + working mode
# Env:
#   AGY_BIN, AGY_INPUT_MODE=argv|stdin, AGY_PRINT_TIMEOUT=5m0s,
#   AGY_HEALTH_TIMEOUT=120 (seconds, wall-clock bound on the sentinel)
# =============================================================================
set -uo pipefail

AGY_BIN="${AGY_BIN:-}"
if [ -z "$AGY_BIN" ]; then
  if command -v agy >/dev/null 2>&1; then AGY_BIN="$(command -v agy)"
  elif [ -x "$HOME/.local/bin/agy" ]; then AGY_BIN="$HOME/.local/bin/agy"
  else AGY_BIN="agy"; fi
fi
AGY_PRINT_TIMEOUT="${AGY_PRINT_TIMEOUT:-5m0s}"
AGY_HEALTH_TIMEOUT="${AGY_HEALTH_TIMEOUT:-120}"
AGY_INPUT_MODE="${AGY_INPUT_MODE:-argv}"

# Portable bounded-exec (no external `timeout`). Captures stdout, enforces a
# wall-clock cap, returns 124 on timeout. Runs "$@" with stdin from a file (or
# /dev/null) so both argv and stdin invocations work.
_bounded() {
  local secs="$1" stdin_file="$2"; shift 2
  local out; out="$(mktemp)"
  ( "$@" <"$stdin_file" >"$out" 2>/dev/null ) &
  local pid=$! i=0
  while kill -0 "$pid" 2>/dev/null; do
    if [ "$i" -ge "$secs" ]; then
      kill -TERM "$pid" 2>/dev/null; sleep 1; kill -KILL "$pid" 2>/dev/null
      wait "$pid" 2>/dev/null || true
      cat "$out"; rm -f "$out"; return 124
    fi
    i=$((i + 1)); sleep 1
  done
  wait "$pid" 2>/dev/null; local rc=$?
  cat "$out"; rm -f "$out"; return "$rc"
}

_run_argv()  { "$AGY_BIN" -p "$1" --sandbox --dangerously-skip-permissions --print-timeout "$AGY_PRINT_TIMEOUT"; }
_run_stdin() { printf '%s' "$1" | "$AGY_BIN" --print --sandbox --dangerously-skip-permissions --print-timeout "$AGY_PRINT_TIMEOUT"; }

_run() {
  case "$AGY_INPUT_MODE" in
    stdin) _run_stdin "$1" ;;
    *)     _run_argv  "$1" ;;
  esac
}

health() {
  [ -x "$AGY_BIN" ] || command -v "$AGY_BIN" >/dev/null 2>&1 || { echo "agy: binary not found ($AGY_BIN)" >&2; return 69; }
  local nul="/dev/null" out
  # try argv form
  out="$(_bounded "$AGY_HEALTH_TIMEOUT" "$nul" "$AGY_BIN" -p 'Reply with exactly: AGY-OK' --sandbox --dangerously-skip-permissions --print-timeout "$AGY_PRINT_TIMEOUT")"
  case "$out" in *AGY-OK*) echo "AGY-OK (mode=argv)"; return 0 ;; esac
  # fall back to stdin form
  local pf; pf="$(mktemp)"; printf 'Reply with exactly: AGY-OK' > "$pf"
  out="$(_bounded "$AGY_HEALTH_TIMEOUT" "$pf" "$AGY_BIN" --print --sandbox --dangerously-skip-permissions --print-timeout "$AGY_PRINT_TIMEOUT")"
  rm -f "$pf"
  case "$out" in *AGY-OK*) echo "AGY-OK (mode=stdin)"; return 0 ;; esac
  echo "agy: UNAVAILABLE — no AGY-OK from either input mode (auth dead / quota / wrong model)" >&2
  return 1
}

main() {
  case "${1:-}" in
    --health|--probe) health ;;
    "" ) _run "$(cat)" ;;
    * ) _run "$1" ;;
  esac
}
main "$@"
