---
description: Diverge over root-cause hypotheses for an observed fault, then falsify cheapest-first — no fix before a hypothesis survives a probe
argument-hint: "[symptom, error, or failing thing to debug]"
---

You are handling the `/ACE:debug $ARGUMENTS` command — hypothesis-divergence debugging of
a fault in the **user's** system.

Boundary check before anything: if the broken thing is an ACE seat itself (empty debate
round, agy returned nothing), route to `/ACE:doctor`. If the user wants a decision or
artifact critiqued rather than a malfunction explained, route to `/ACE:debate`.

**Do this, in order:**

1. **Read the skill in full:** `skills/ace-debug/SKILL.md` in this plugin. It carries the
   layer catalog for hypothesis divergence, the discrimination-per-cost ranking, the
   falsification-ladder rules, and the escalation gate. Follow it; do not improvise.
2. **Symptom.** If `$ARGUMENTS` is non-empty, treat it as the symptom. Either way, run the
   skill's intake before hypothesizing: exact error text verbatim, repro command and its
   reliability, and what changed closest to onset.
3. **Diverge on Claude.** Generate 4–7 hypotheses across distinct causal layers (code,
   data, deps, config, environment, timing, observer). The external seat is an escalation,
   not the baseline — do not dispatch quota on round one.
4. **Falsify cheapest-first.** For each probe, state the expected observation per surviving
   hypothesis BEFORE running it. After each probe, name what died. Refuse shotgun fixes.
5. **Escalate only per the skill's gate** (two dry rounds, self-anchoring, or high stakes) —
   and run `/ACE:doctor` first if this session has not. Privacy-bound logs/tracebacks go to
   `ollama` or stay on Claude; never to `agy`.
6. **Fix only after survival**, then re-run the original repro to verify. If the user asked
   for diagnosis only, stop at the surviving hypothesis and report.

The rule that makes this command trustworthy: **a vanished symptom with an unconfirmed
cause is reported exactly as that** — never as "fixed".
