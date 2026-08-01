---
description: Run a cognitive-divergence debate on a decision — frames plus an optional cross-family seat
argument-hint: "[topic or decision to debate]"
---

You are handling the `/ACE:debate $ARGUMENTS` command — run a structured cognitive-divergence
debate using the ACE engine.

Debate is ACE's **divergence** command: it widens and stress-tests the option space and hands back
a branch set plus a synthesis prompt. It does **not** return a decision. If the user already knows
what to do and wants ordered steps, stop and route them to `/ACE:plan` instead.

**Do this, in order:**

1. **Load the depth.** Read the `ace-debate` skill (`skills/ace-debate/SKILL.md` in this plugin)
   in full before running anything. It carries the real engine flow, the verified CLI flags, the
   zombie-gate reading guide, and a live engine defect you must work around.
2. **Topic.** If `$ARGUMENTS` is non-empty, use it as the debate topic. If empty, ask for it.
3. **Stakes question.** Ask whether this decision is *high-stakes* (irreversible, expensive, or
   safety-relevant). If yes, dispatch the cross-family `agy` seat **unconditionally** — do not wait
   for the shared-blind-spot alarm, which only catches vocabulary collapse.
4. **Preflight before spending quota.** The `ace` on PATH is **not** this branch —
   `/usr/local/bin/ace` resolves to `/Users/sebastianziegler/ace/ace/__init__.py`, the owner's
   working tree, which has no `banner`, no `--mode` and no `--coherence-floor`. Always invoke the
   worktree build. System `python3` is 3.9 and cannot import the package.

   ```bash
   cd /Users/sebastianziegler/ace
   ~/.claude/scripts/adapters/doctor.sh --fast
   /usr/local/bin/python3.11 -m ace.cli banner --preset <preset> --providers <seats>
   ```

   Show the output verbatim. Never hand-write a provider status row — a row is a PATH lookup, not
   proof the seat produces branches.
5. **Run.** `ace run` prompts interactively for a synthesis focus at the end of *each* cycle. In a
   non-interactive shell (the Bash tool) that prompt raises `Abort` and kills the run **after** the
   seat has already been dispatched and quota spent, so always feed the choice on stdin — one line
   per cycle:

   ```bash
   printf '2\n' | /usr/local/bin/python3.11 -m ace.cli run "<topic>" \
     --preset <preset> --cycles <n> --providers <seats>
   ```

   (`2` = Load-bearing vs noise; `4` = Full Governor. Full menu is in the skill.) `--preset` alone
   already sets the root mode, so `--mode` is unnecessary. Only `agy` and `ollama` are valid seat
   names on this branch; an all-unknown `--providers` list crashes. **`ollama` is a privacy/bulk
   seat, never a debate peer** — select it only when the topic cannot leave the box, and discount
   its branches on read. When quota is out and the topic is not privacy-bound, run the frames on
   Claude in this conversation instead of substituting the local seat.
6. **Aggregate asymmetrically.** This is the rule that makes the command trustworthy:
   an external seat's **disagreement** is a flag to re-examine with the strong model; its
   **agreement counts for nothing**; no external seat ever gets a vote that overturns Claude.
   Never report a tally like "2 of 3 agreed" — report what was disagreed about.
7. **Synthesize.** Take the panel `ace run` prints and answer it in this conversation. Then state
   plainly that there was no rebuttal round — branches never saw each other.

Seat names, frame catalog, triage table, and incident chronicles all live in the skill and its
`references/` files. Do not re-derive any of it from memory.
