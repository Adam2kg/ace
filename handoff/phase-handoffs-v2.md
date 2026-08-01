# Handoff Protocol v2 (ACE)  — STAGED, applies at cutover

> Status: staged. At migration cutover this content replaces
> `~/.claude/phase-handoffs.md`, and RULE #2 in `~/.claude/CLAUDE.md` is
> updated to point at `.handoff.md` / `.handoffs/`. Until then the v1 protocol
> remains live. This is the *writer* half of handoff v2; the *reader* half is
> `~/.claude/scripts/handoff-v2.sh` (the SessionStart hook).

When you conclude a work phase, or when context is filling up (RULE #2), or when
the user says "done"/"next phase"/"wrap up", you MUST write a handoff before the
session ends. The auto-resume hook depends on this file existing and being
well-formed.

## Where

- **Live handoff:** `<project-root>/.handoff.md` — overwritten each time; this is
  what the SessionStart hook reads. Always write it at the **project root** (the
  dir Claude Code is launched from), never a subdir — the hook reads `$cwd/.handoff.md`.
- **Archive copy:** `<project-root>/.handoffs/<phase>-<YYYYMMDD-HHMMSS>.md` — the
  permanent record. Create `.handoffs/` if absent. Never overwrite an archive file.

## Exact format (the hook parses the `@` sentinels)

```
@next: <one concrete resume command — e.g. /ACE:plan wire routing into divergence.py>
@topic: <optional alternative thread 1>
@topic: <optional alternative thread 2>
@topic: <optional alternative thread 3>
@project: <absolute path of the project root>

# Session Handoff: <short title>
Completed: <ISO-8601 UTC, e.g. 2026-07-24T14:00:00Z>
Phase: <phase name>  |  Next: <next phase>

## What was accomplished
- <2-5 concrete outcomes>

## Key decisions
- <significant choices + rationale>

## Inputs for next phase
- <specific findings, constraints, open questions the next session needs>

## Blockers / watch-outs
- <anything that could block progress, or "none">

## Resume
Choose the menu's "Resume" option (runs `@next` directly), or pick a topic.
```

### Sentinel rules (hard requirements — the hook enforces them)

- **`@next:` is REQUIRED.** Its value is the literal command a "Resume" click will
  run, so it must be a real, runnable next action — not a description. If you
  cannot name a concrete next command, the phase is not done enough to hand off.
  A file without `@next:` is treated as corrupt and the hook stays silent.
- **`@`-lines start at column 0** and use these exact prefixes. Narrative prose must
  never begin a line with `@…:` (the hook greps `^@`), so keep prose indented or
  prefixed with `#`/`-`.
- **`@topic:`** — 0 to 3 lines. Each becomes one menu option ("Topic N: …"). More
  than 3 are ignored by the menu (still fine in the body). Use these for genuinely
  distinct alternative threads the next session might pick instead of resuming.
- **`@project:`** — advisory; record the absolute project root.
- **`Completed:`** — ISO-8601 UTC. The hook computes staleness from this (not mtime),
  so a stale handoff is *labeled* ("Resume anyway (N days old)"), never hidden, and
  a `touch` cannot fake freshness.

## Consumption (prevents re-prompting every session)

After the user chooses **Resume** and you have actually begun the next phase's
work, **move** `.handoff.md` into the archive:
`mv .handoff.md .handoffs/<phase>-<YYYYMMDD-HHMMSS>.md`. This is why the next fresh
session does not re-show a menu for work already resumed. (If you wrote a fresh
archive copy at handoff time, moving the live file is enough; do not double-archive.)

## Announce

After writing the handoff, tell the user: the file was written; that a new session
will auto-open the resume menu (one click, no re-typing); and the concrete `@next`
command that "Resume" will run.

## Migration note (remove after cutover soak)

During migration the hook also falls back to a legacy `~/…/.octo-continue.md` when
no `.handoff.md` exists, so in-flight projects keep resuming. New handoffs should
always be written in the v2 format above. Once all live projects have a `.handoff.md`,
the legacy fallback and any remaining `.octo-continue.md` files can be retired.
