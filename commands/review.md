---
description: Cross-family decorrelated review of a diff or PR — escalation beyond Claude-native /code-review, asymmetric aggregation
argument-hint: "[diff, branch, or PR to review]"
---

You are handling the `/ACE:review $ARGUMENTS` command — a decorrelated second-family
review of a **concrete diff**.

Boundary checks before anything: for an ordinary review, Claude-native `/code-review` is
the right tool — say so and use it; this command exists to ADD one independent-family pass
on a high-stakes diff, not to replace the native review. If the target is a design doc,
RFC, plan, or threat model, route to `/ACE:debate`.

**Do this, in order:**

1. **Read the skill in full:** `skills/ace-review/SKILL.md` in this plugin. It carries the
   native-first rule, the escalation-set selection, the privacy gate, the refutation
   prompt discipline, and the asymmetric aggregation rules. Follow it; do not improvise.
2. **Scope.** If `$ARGUMENTS` names a branch/PR/diff, use it; otherwise ask. Run or ingest
   the native review first.
3. **Select the escalation set** — the 1–5 load-bearing hunks where being wrong is
   expensive. Never ship the whole diff to a seat.
4. **Privacy gate.** Sending code to `agy` sends it to a third party. Confirm with the user
   once per session that this diff may leave the box; proprietary/PII-adjacent code goes to
   `ollama` (model pinned) or gets an adversarial frames pass on Claude instead. Never
   decide this silently.
5. **Doctor before dispatch** if this session has not run it — a zombie seat's empty "LGTM"
   is vacuous agreement counted as a clean bill.
6. **Refutation-prompt each hunk** to the seat, then **aggregate asymmetrically**: seat
   disagreement = candidate finding to verify against the code; seat agreement = nothing.
   Never report a tally, never let seat approval overturn a native finding.
7. **Report** confirmed findings first (file:line + concrete failure scenario), unverified
   candidates labeled as such, and state exactly which hunks got the decorrelated pass.
   Post no PR comments and push nothing without confirmation.
