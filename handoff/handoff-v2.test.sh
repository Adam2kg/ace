#!/bin/bash
# Prove-phase test harness for handoff-v2.sh
# Runs the hook under /bin/bash (3.2) against synthetic SessionStart payloads.
set -u
HOOK="$HOME/.claude/scripts/handoff-v2.sh"
ROOT="$(mktemp -d)"
PASS=0; FAIL=0
say() { printf '%s\n' "$*"; }
ok()   { PASS=$((PASS+1)); printf '  \033[32mPASS\033[0m %s\n' "$1"; }
bad()  { FAIL=$((FAIL+1)); printf '  \033[31mFAIL\033[0m %s\n' "$1"; }

# run <dir> <source> -> stdout of hook, via /bin/bash (force 3.2 path)
run() {
  printf '{"cwd":"%s","source":"%s","hook_event_name":"SessionStart"}' "$1" "$2" \
    | /bin/bash "$HOOK"
}
# assert output is empty
assert_empty() { if [ -z "$1" ]; then ok "$2"; else bad "$2 (expected empty, got: ${1:0:60}...)"; fi; }
# assert valid json
assert_json() { if printf '%s' "$1" | jq -e . >/dev/null 2>&1; then ok "$2"; else bad "$2 (invalid JSON)"; fi; }
# assert jq filter true
assert_jq() { if printf '%s' "$1" | jq -e "$2" >/dev/null 2>&1; then ok "$3"; else bad "$3"; fi; }
# assert additionalContext contains substring
assert_ac_has() {
  local ac; ac="$(printf '%s' "$1" | jq -r '.hookSpecificOutput.additionalContext // ""' 2>/dev/null)"
  case "$ac" in *"$2"*) ok "$3";; *) bad "$3 (context missing: $2)";; esac
}

say ""
say "=========================================================="
say " handoff-v2.sh — Prove-phase test suite"
say " test root: $ROOT"
say "=========================================================="

# ---- Case 1: valid v2 handoff, startup --------------------------------------
say ""; say "[1] Valid v2 handoff (startup) — full menu, both fields"
D1="$ROOT/proj1"; mkdir -p "$D1"
cat > "$D1/.handoff.md" <<EOF
@next: /ACE:plan wire routing into divergence.py
@topic: Close the zombie-gate in every provider runner
@topic: Prune divergence.py dead runners
@project: $D1

# Session Handoff: ACE routing build
Completed: $(date -u +%Y-%m-%dT%H:%M:%SZ)
Phase: develop  |  Next: /ACE:plan
## What was accomplished
Built the routing table.
EOF
O1="$(run "$D1" startup)"
assert_json "$O1" "output is valid JSON"
assert_jq  "$O1" '.hookSpecificOutput.hookEventName=="SessionStart"' "hookEventName correct"
assert_jq  "$O1" '.hookSpecificOutput.additionalContext|type=="string" and length>0' "additionalContext present"
assert_jq  "$O1" '.hookSpecificOutput.initialUserMessage|type=="string" and length>0' "initialUserMessage present (forces opening turn)"
assert_jq  "$O1" '.hookSpecificOutput.sessionTitle=="Session Handoff: ACE routing build"' "sessionTitle from H1"
assert_ac_has "$O1" "AskUserQuestion" "instructs AskUserQuestion call"
assert_ac_has "$O1" "/ACE:plan wire routing into divergence.py" "resume option carries @next command"
assert_ac_has "$O1" "Topic 1: Close the zombie-gate" "topic 1 parsed"
assert_ac_has "$O1" "Topic 2: Prune divergence.py" "topic 2 parsed"
assert_ac_has "$O1" "Start something else" "escape option present"
assert_ac_has "$O1" "What was accomplished" "full body injected as context"

# ---- Case 2: no handoff -> silent -------------------------------------------
say ""; say "[2] No handoff in dir — silent, exit 0"
D2="$ROOT/proj2"; mkdir -p "$D2"
O2="$(run "$D2" startup)"
assert_empty "$O2" "emits nothing when no handoff exists"

# ---- Case 3: corrupt handoff (no @next) -> silent zombie gate ---------------
say ""; say "[3] Corrupt v2 handoff (no @next sentinel) — zombie gate, silent"
D3="$ROOT/proj3"; mkdir -p "$D3"
cat > "$D3/.handoff.md" <<EOF
# Half-written handoff
Completed: $(date -u +%Y-%m-%dT%H:%M:%SZ)
Some narrative but the @next line never got written.
EOF
O3="$(run "$D3" startup)"
assert_empty "$O3" "corrupt handoff (missing @next) emits nothing, no crash"

# ---- Case 4: stale handoff -> surfaced with age label -----------------------
say ""; say "[4] Stale v2 handoff (30 days old) — surfaced, labeled, not suppressed"
D4="$ROOT/proj4"; mkdir -p "$D4"
OLD="$(date -u -j -v-30d +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -d '30 days ago' +%Y-%m-%dT%H:%M:%SZ)"
cat > "$D4/.handoff.md" <<EOF
@next: /ACE:debate revisit the provider roster
@project: $D4

# Old handoff
Completed: $OLD
EOF
O4="$(run "$D4" startup)"
assert_json "$O4" "stale handoff still produces output (not suppressed)"
assert_ac_has "$O4" "days old" "staleness surfaced as a label"
assert_ac_has "$O4" "/ACE:debate revisit the provider roster" "stale resume command still offered"

# ---- Case 5: legacy .octo-continue.md fallback ------------------------------
say ""; say "[5] Legacy .octo-continue.md (no sentinels) — migration fallback works"
D5="$ROOT/proj5"; mkdir -p "$D5"
cat > "$D5/.octo-continue.md" <<EOF
Project: $D5
# 🐙 Phase Handoff: develop
## What was accomplished
Legacy narrative handoff, no @next sentinel.
EOF
O5="$(run "$D5" startup)"
assert_json "$O5" "legacy handoff produces valid output"
assert_ac_has "$O5" "Resume where the last session left off" "legacy generic-resume label"
assert_ac_has "$O5" "Legacy narrative handoff" "legacy body injected"

# ---- Case 6: compact source -> additionalContext ONLY -----------------------
say ""; say "[6] source=compact — context only, NO initialUserMessage (no turn hijack)"
O6="$(run "$D1" compact)"
assert_json "$O6" "compact output valid JSON"
assert_jq  "$O6" '.hookSpecificOutput.additionalContext|type=="string"' "compact keeps additionalContext"
assert_jq  "$O6" '.hookSpecificOutput|has("initialUserMessage")|not' "compact OMITS initialUserMessage"

# ---- Case 7: resume + clear sources also get full menu ----------------------
say ""; say "[7] source=resume and source=clear — both get full auto-menu"
O7a="$(run "$D1" resume)"; O7b="$(run "$D1" clear)"
assert_jq "$O7a" '.hookSpecificOutput.initialUserMessage|length>0' "resume source forces turn"
assert_jq "$O7b" '.hookSpecificOutput.initialUserMessage|length>0' "clear source forces turn"

# ---- Case 8: v2 preferred over legacy when both exist -----------------------
say ""; say "[8] Both .handoff.md and .octo-continue.md present — v2 wins"
D8="$ROOT/proj8"; mkdir -p "$D8"
printf '@next: /ACE:plan the-v2-one\n\n# V2\nCompleted: %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$D8/.handoff.md"
printf 'Project: %s\n# legacy\nthe-legacy-one\n' "$D8" > "$D8/.octo-continue.md"
O8="$(run "$D8" startup)"
assert_ac_has "$O8" "the-v2-one" "v2 handoff preferred when both exist"

# ---- Case 9: empty handoff file -> silent -----------------------------------
say ""; say "[9] Empty .handoff.md — silent"
D9="$ROOT/proj9"; mkdir -p "$D9"; : > "$D9/.handoff.md"
O9="$(run "$D9" startup)"
assert_empty "$O9" "empty handoff file emits nothing"

# ---- Case 10: >3 topics -> capped at 3 --------------------------------------
say ""; say "[10] More than 3 @topic lines — capped at 3"
D10="$ROOT/proj10"; mkdir -p "$D10"
cat > "$D10/.handoff.md" <<EOF
@next: /ACE:plan x
@topic: one
@topic: two
@topic: three
@topic: four-should-be-dropped
Completed: $(date -u +%Y-%m-%dT%H:%M:%SZ)
# t
EOF
O10="$(run "$D10" startup)"
assert_ac_has "$O10" "Topic 3: three" "third topic kept as an option"
# invariant: the 4th topic must NOT appear as a menu OPTION line (body may mention it)
if printf '%s' "$O10" | jq -r '.hookSpecificOutput.additionalContext' | grep -qE '"Topic 4:'; then
  bad "4th topic leaked into options"
else
  ok "no 'Topic 4:' option (menu capped at 3 topics)"
fi

# ---- Case 11: option-count bound 2..4 across all topic counts ---------------
say ""; say "[11] AskUserQuestion 2-4 option bound holds for 0,1,2,3 topics"
count_opts() { printf '%s' "$1" | jq -r '.hookSpecificOutput.additionalContext' \
  | grep -cE '^  [0-9]+\. "'; }
for n in 0 1 2 3; do
  DD="$ROOT/optn$n"; mkdir -p "$DD"
  { echo "@next: /ACE:plan x"; i=0; while [ "$i" -lt "$n" ]; do echo "@topic: t$i"; i=$((i+1)); done; \
    echo "Completed: $(date -u +%Y-%m-%dT%H:%M:%SZ)"; echo "# h"; } > "$DD/.handoff.md"
  ON="$(count_opts "$(run "$DD" startup)")"
  if [ "$ON" -ge 2 ] && [ "$ON" -le 4 ]; then ok "$n topics -> $ON options (within 2-4)"; else bad "$n topics -> $ON options (OUT OF BOUNDS)"; fi
done

say ""
say "=========================================================="
printf " RESULT: \033[32m%d passed\033[0m, \033[31m%d failed\033[0m\n" "$PASS" "$FAIL"
say "=========================================================="
rm -rf "$ROOT"
[ "$FAIL" -eq 0 ]
