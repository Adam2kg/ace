# Migration: replace auth-dead `gemini` runner with Antigravity (`agy`)

**Status:** PENDING (spec only — not implemented)
**Drafted:** 2026-06-21
**Do this in an ACE session** (`claude ~/ace`), not from the claude-octopus repo.

## Why

ACE's `gemini` divergence seat is a **zombie**: `command -v gemini` still finds the binary,
so it passes the availability gate in `_run_gemini`, but the Gemini CLI **auth is dead** on
this machine. Result — the runner silently yields no branches at runtime (worse than a
missing provider, because the gate reports it available).

Octopus already migrated this seat: **`agy` (Antigravity)** is the authed, working non-Claude
provider, running **Gemini 3.5 Flash** under the hood. So the *model diversity survives* —
only the *CLI* changes (`gemini` → `agy`).

## Edits

### 1. `ace/agents/divergence.py`
- Add `_run_agy(topic, frame_id)` modeled on `_run_gemini` (currently ~lines 164–187), but
  shell out to `agy`. **Crib the exact non-interactive invocation flags from Octopus's
  `agy-exec.sh`** rather than guessing.
  - Octo notes: `agy --print` has a hardcoded 30s auth wait; auth is already done
    (interactive Google OAuth, smoke returns `AGY-OK`). Model = the `/model`-selected default
    (currently Gemini 3.5 Flash); override via `OCTOPUS_AGY_MODEL`.
  - Mark `available=False` on empty/error output (same pattern the other runners use) — this
    is the fix for the zombie-gate class of bug.
- `runners` dict (~line 339): swap `"gemini": _run_gemini` → `"agy": _run_agy`
  (or keep `gemini` as a legacy entry and add `agy` alongside).
- Frame assignments (~line 103): move `["biology", "markets", "ten-year-old", "regulator"]`
  from `"gemini"` → `"agy"`.
- Header comment (~lines 5–6): relabel `🟡 Gemini` → `🧭 Antigravity`.

### 2. `skills/ace.md`
- Step 3 provider check (~lines 83–84) and banner (~lines 90–91): `gemini` → `agy`,
  emoji `🟡` → `🧭`.
- Line ~342 "external Gemini review" is prose history — leave it.

### 3. Global `/ace` command — NO CHANGE
`~/.claude/commands/ace.md` defers the banner to skill Step 3, so it inherits this change.

### 4. Tests
`python3 -m pytest`. Add an `_run_agy` test if the other runners have coverage
(check `tests/` for existing divergence runner tests).

## Acceptance
- `ace run "<topic>" --providers agy` produces real branches (not empty).
- Provider banner shows 🧭 Antigravity, not 🟡 Gemini.
- Zombie gate closed: an unauthed/empty `agy` run is reported unavailable, not silently empty.
