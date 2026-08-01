#!/usr/bin/env bash
# doctor.sh — consolidated ACE provider health (the /ACE:doctor engine).
# =============================================================================
# One command, all seats, zombie-safe: every check exercises the seat's REAL
# invocation and verifies actual output (sentinel/content), never mere binary
# presence. This is the once-per-session health surface SPEC §3.2 specifies.
#
# Usage:  doctor.sh          full check (agy included — costs ~10s)
#         doctor.sh --fast   skip agy (the slow seat); local + openai only
# Exit:   0 = every checked seat healthy
#         1 = at least one seat unhealthy (details on stdout)
# =============================================================================
set -uo pipefail
A="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
FAST=0; [ "${1:-}" = "--fast" ] && FAST=1
FAIL=0

line() { printf '%-8s %s\n' "$1" "$2"; }

echo "ACE provider health — $(date '+%Y-%m-%d %H:%M')"
echo "─────────────────────────────────────────────"

# ollama (local) — fast, free
if OUT="$("$A/ollama.sh" --health 2>&1)"; then line "ollama" "✅ $OUT"; else line "ollama" "❌ $OUT"; FAIL=1; fi

# openai (cloud, different family) — status-aware
if OUT="$("$A/openai.sh" --health 2>&1 | head -1)"; then
  line "openai" "✅ $OUT"
else
  RC=$?
  case "$RC" in
    3|4) line "openai" "⚠️  $OUT (transient — key not disproven)" ;;
    *)   line "openai" "❌ $OUT"; FAIL=1 ;;
  esac
fi

# agy (Gemini family) — slow (~8s); skipped in --fast
if [ "$FAST" -eq 1 ]; then
  line "agy" "⏭  skipped (--fast)"
else
  if OUT="$("$A/agy.sh" --health 2>&1)"; then line "agy" "✅ $OUT"; else line "agy" "❌ $OUT"; FAIL=1; fi
fi

# handoff v2 — the migration precondition; presence + parse, not just test -f
HV2="$HOME/.claude/scripts/handoff-v2.sh"
if [ -x "$HV2" ] && /bin/bash -n "$HV2" 2>/dev/null; then
  line "handoff" "✅ handoff-v2.sh present + parses"
else
  line "handoff" "❌ handoff-v2.sh missing or unparseable"; FAIL=1
fi

echo "─────────────────────────────────────────────"
if [ "$FAIL" -eq 0 ]; then echo "ALL SEATS HEALTHY"; else echo "DEGRADED — see ❌ above (Claude-only floor still available)"; fi
exit "$FAIL"
