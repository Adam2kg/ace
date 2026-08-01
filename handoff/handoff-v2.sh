#!/usr/bin/env bash
# handoff-v2.sh — SessionStart hook (ACE handoff system, v2)
# =============================================================================
# Auto-resumes where the last session's handoff left off by making Claude open
# the session with a clickable AskUserQuestion menu — no manual re-prompting.
#
# Emits a SessionStart JSON envelope carrying BOTH:
#   - additionalContext : passive, always lands in context (the always-works path)
#   - initialUserMessage: active, materializes the opening turn so the menu renders
# On `compact` it emits additionalContext ONLY (never hijacks a mid-session turn).
#
# Reads $cwd/.handoff.md (v2), falling back to legacy $cwd/.octo-continue.md
# during migration. Writes nothing (and exits 0) when there is no valid handoff,
# so it is safe on every session.
#
# Verified against Claude Code 2.1.217 (Desktop) / 2.1.205 (CLI):
#   hookSpecificOutput.{hookEventName,additionalContext,initialUserMessage,sessionTitle}
#   source enum: startup | resume | clear | compact
#
# Portability: written for bash 3.2 (macOS /bin/bash). No mapfile, no assoc
# arrays. Every grep is guarded so a no-match never trips `set -e`.
# =============================================================================
set -euo pipefail

FRESH_DAYS=7   # staleness is a LABEL, never a suppressor (see below)

# --- fail-safe: any unexpected error => emit nothing, exit 0 (never block start)
_bail() { exit 0; }
trap _bail ERR

# --- read the SessionStart payload from stdin -------------------------------
PAYLOAD="$(cat 2>/dev/null || true)"
CWD=""; SOURCE=""
if [ -n "$PAYLOAD" ] && command -v jq >/dev/null 2>&1; then
  CWD="$(printf '%s' "$PAYLOAD" | jq -r '.cwd // empty' 2>/dev/null || true)"
  SOURCE="$(printf '%s' "$PAYLOAD" | jq -r '.source // empty' 2>/dev/null || true)"
fi
[ -n "$CWD" ] || CWD="$PWD"
[ -n "$SOURCE" ] || SOURCE="startup"

# --- locate the handoff file (v2 preferred, legacy fallback) ----------------
V2="$CWD/.handoff.md"
LEGACY="$CWD/.octo-continue.md"
H=""; IS_LEGACY=0
if [ -f "$V2" ] && [ -s "$V2" ]; then
  H="$V2"
elif [ -f "$LEGACY" ] && [ -s "$LEGACY" ]; then
  H="$LEGACY"; IS_LEGACY=1
fi
[ -n "$H" ] || exit 0   # no handoff here — silent, safe

# --- parse sentinels (guarded so no-match cannot crash under set -e) ---------
NEXT="$(grep -m1 '^@next:'    "$H" 2>/dev/null | sed 's/^@next:[[:space:]]*//'    || true)"
PROJECT="$(grep -m1 '^@project:' "$H" 2>/dev/null | sed 's/^@project:[[:space:]]*//' || true)"

# up to 3 @topic: lines, collected without mapfile (bash 3.2 safe)
TOPIC1=""; TOPIC2=""; TOPIC3=""; TN=0
while IFS= read -r line; do
  [ -n "$line" ] || continue
  TN=$((TN + 1))
  case "$TN" in
    1) TOPIC1="$line" ;;
    2) TOPIC2="$line" ;;
    3) TOPIC3="$line" ;;
  esac
  [ "$TN" -ge 3 ] && break
done <<EOF
$(grep '^@topic:' "$H" 2>/dev/null | sed 's/^@topic:[[:space:]]*//' || true)
EOF

# --- ZOMBIE GATE ------------------------------------------------------------
# A v2 handoff MUST carry an @next: sentinel. Its absence => not a real v2
# handoff (half-written / corrupt) => emit nothing, exit 0 (not a crash).
# Legacy .octo-continue.md has no sentinels and is narrative-only; it is
# allowed through the gate on a different path (generic resume).
if [ "$IS_LEGACY" -eq 0 ] && [ -z "$NEXT" ]; then
  exit 0
fi

# --- staleness: computed from Completed: timestamp, mtime only as fallback ---
COMPLETED="$(grep -m1 '^Completed:' "$H" 2>/dev/null | sed 's/^Completed:[[:space:]]*//' || true)"
TS=""
if [ -n "$COMPLETED" ]; then
  # try full ISO-8601 UTC, then date-only; BSD date (macOS) syntax
  TS="$(date -j -u -f "%Y-%m-%dT%H:%M:%SZ" "$COMPLETED" +%s 2>/dev/null || true)"
  [ -n "$TS" ] || TS="$(date -j -u -f "%Y-%m-%d" "${COMPLETED%%T*}" +%s 2>/dev/null || true)"
fi
[ -n "$TS" ] || TS="$(stat -f %m "$H" 2>/dev/null || stat -c %Y "$H" 2>/dev/null || echo 0)"
NOW="$(date +%s)"
AGE_DAYS=$(( (NOW - TS) / 86400 ))
[ "$AGE_DAYS" -lt 0 ] && AGE_DAYS=0
STALE=0
[ "$AGE_DAYS" -ge "$FRESH_DAYS" ] && STALE=1

# --- session title (polish): first markdown H1, else project basename -------
TITLE="$(grep -m1 '^# ' "$H" 2>/dev/null | sed 's/^#[[:space:]]*//' || true)"
if [ -z "$TITLE" ]; then
  base_src="${PROJECT:-$CWD}"
  TITLE="Resume: $(basename "$base_src")"
fi

# --- build the resume option label ------------------------------------------
if [ "$IS_LEGACY" -eq 1 ]; then
  RESUME_ACTION="continue exactly where the handoff narrative left off"
  RESUME_LABEL="Resume where the last session left off"
else
  RESUME_ACTION="run this command: $NEXT"
  RESUME_LABEL="Resume: $NEXT"
fi
if [ "$STALE" -eq 1 ]; then
  RESUME_LABEL="Resume anyway ($AGE_DAYS days old): ${RESUME_LABEL#Resume: }"
fi

# --- assemble the option list Claude must present ---------------------------
# HARD CONSTRAINT: AskUserQuestion accepts 2-4 explicit options and ALWAYS
# auto-adds an "Other" + freeform choice on top. So: option 1 = Resume, then
# up to 3 topics (max 4 total). An explicit "Start something else" is added
# ONLY when there is room (< 4 so far) — which also guarantees the 2-option
# minimum in the zero-topic case. At the 4-option ceiling (resume + 3 topics)
# the auto-added "Other" serves as the escape.
OPTS="  1. \"$RESUME_LABEL\" — $RESUME_ACTION"
ON=1
for t in "$TOPIC1" "$TOPIC2" "$TOPIC3"; do
  [ -n "$t" ] || continue
  ON=$((ON + 1))
  OPTS="$OPTS
  $ON. \"Topic $((ON-1)): $t\" — start this thread instead of resuming"
done
if [ "$ON" -lt 4 ]; then
  ON=$((ON + 1))
  if [ "$STALE" -eq 1 ]; then
    OPTS="$OPTS
  $ON. \"Start fresh (discard this handoff)\" — do not resume; ask what to work on"
  else
    OPTS="$OPTS
  $ON. \"Start something else\" — do not resume; ask what to work on"
  fi
fi

HDR="SESSION HANDOFF DETECTED for this project ($H)."
[ "$STALE" -eq 1 ] && HDR="$HDR NOTE: this handoff is $AGE_DAYS days old (older than $FRESH_DAYS-day freshness window) — surface it, but flag the age."

# --- the full handoff body (jq --arg handles all escaping) ------------------
BODY="$(cat "$H" 2>/dev/null || true)"

read -r -d '' INSTRUCTION <<EOF || true
$HDR

You are opening a session that has a saved handoff. Your VERY FIRST action must
be to call the AskUserQuestion tool exactly once so the user resumes with a
single click — do not write a narrative preamble first.

AskUserQuestion parameters:
  - header: "Resume"
  - question: "Pick up where the last session left off, or start elsewhere?"
  - options (present EXACTLY these, in THIS order — do not add or invent any):
$OPTS

The tool automatically adds an "Other" choice with a freeform field; do NOT add
your own — these options plus "Other" are the complete set (2-4 explicit max).

Behavior after the user chooses:
  - Option 1 (Resume): $RESUME_ACTION. Use the full handoff context below.
  - A "Topic N" option: begin that thread; the handoff body is still context.
  - "Start something else" / "Start fresh" / the auto-added Other/freeform:
    do not resume — ask what they want to work on.
  - On any resume, once you have actually started the work, move the handoff to
    the archive dir ($CWD/.handoffs/) so it does not re-prompt next session.

--- HANDOFF CONTENT (full context for whatever the user picks) ---
$BODY
--- END HANDOFF CONTENT ---
EOF

# initialUserMessage: the short trigger that forces the opening turn.
# If a surface ignores it (e.g. terminal TTY), additionalContext still makes
# Claude open with the menu on the user's first keystroke — safe degradation.
TRIGGER="Resume this project — show me the handoff menu."

# --- emit the verified SessionStart envelope --------------------------------
case "$SOURCE" in
  startup|resume|clear)
    jq -n \
      --arg ac "$INSTRUCTION" \
      --arg ium "$TRIGGER" \
      --arg title "$TITLE" \
      '{hookSpecificOutput: {hookEventName: "SessionStart", additionalContext: $ac, initialUserMessage: $ium, sessionTitle: $title}}'
    ;;
  *)  # compact (or any unknown source): restore context, never force a menu turn
    jq -n \
      --arg ac "$INSTRUCTION" \
      '{hookSpecificOutput: {hookEventName: "SessionStart", additionalContext: $ac}}'
    ;;
esac

exit 0
