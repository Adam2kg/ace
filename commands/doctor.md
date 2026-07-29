---
description: Check ACE provider seat health (agy, ollama, openai) — zombie-safe, once per session
argument-hint: "[--fast]"
---

You are handling the `/ACE:doctor $ARGUMENTS` command — a **health check only**. It runs no
debate, produces no plan, and answers exactly one question: *which ACE seats can be trusted
right now?*

The canonical instructions live in the ACE plugin so they never drift from the adapters.
Do this:

1. **Read** `skills/ace-doctor/SKILL.md` (this plugin) in full before interpreting anything.
2. **Run the engine** and show its output verbatim.

   Run `~/.claude/scripts/adapters/doctor.sh --fast` **by default** (T1 — free, skips the
   paid agy seat):

   ```bash
   ~/.claude/scripts/adapters/doctor.sh --fast
   ```

   Run the full `~/.claude/scripts/adapters/doctor.sh` (T3 — spends agy OAuth quota, ~10s)
   **only** when the user asked for a full check, said `--fast` was not enough, or is about
   to dispatch agy. Never loop either form.

3. **Report statuses ONLY from that output.** Never infer, guess, or hand-write a seat row.
   A binary being installed is not health — `ace banner` uses a PATH lookup and will happily
   print `available ✓` for a dead seat. Doctor wins when they disagree.
4. **If `--fast` was used, agy was NOT exercised.** doctor.sh still prints `ALL SEATS
   HEALTHY` with the agy row at `⏭ skipped`. Do not pass that through. Report it as:
   "ollama, openai, handoff healthy — agy NOT CHECKED (--fast). Re-run `/ACE:doctor`
   without --fast before any work that needs the decorrelated seat."
5. **Check the `ollama` row's parenthetical, not just the ✅.** If it reads `sentinel
   drift: …`, the seat generated text but ignored the instruction — exit is still 0 and the
   summary still says healthy. Report it as a partial pass: fine for bulk extraction, treat
   as **down** for anything where output shape matters.
6. **If any seat is ❌ or ⚠️**, look it up in the SKILL's symptom → diagnosis → fix table and
   give the user the specific fix, including the exit code. Do not paraphrase from memory —
   the 401-vs-429-vs-5xx distinction matters (a 5xx does **not** mean the key is dead). If
   agy failed only after hanging for minutes, suspect a timeout, not dead auth — the exit
   code is 1 either way.
7. **State the degradation consequence** in plain words: which capability is lost and what
   ACE will do instead. A downed external seat degrades ACE to **frames-on-Claude**, not to
   nothing — frames are the default diversity mechanism; only cross-family
   error-decorrelation is lost. If the user's next task is privacy-bound and ollama is
   down, say STOP — never suggest a cloud fallback for PII.

Do **not** re-run individual paid seats (`agy.sh --health`, `openai.sh --health`) on top of
a full `doctor.sh` run; doctor already exercised them. `openai` is a **manual adapter seat
only** — there is no `_run_openai` in the engine, so never tell the user to pass
`--providers openai` to `ace run`.
