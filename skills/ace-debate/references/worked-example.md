# /ACE:debate — worked example, end to end

The skeleton lives in `../SKILL.md`. This is the full narrative, with real pasted output.

**Question:** should the 360-editor frame index use SQLite R-tree or Postgres PostGIS?
Reversible, moderate stakes, one live cross-family seat available.

All commands run from the worktree, because the `ace` on PATH is a different, older build
(see [troubleshooting.md §7](troubleshooting.md)).

---

## Step 1 — preflight (T1)

Confirm the seat is real before spending quota.

```bash tier=T3 verified=2026-07-29
cd /Users/sebastianziegler/ace-unify
~/.claude/scripts/adapters/doctor.sh --fast
/usr/local/bin/python3.11 -m ace.cli banner --preset architecture --providers agy
```

Actual output on this branch (T1, executed 2026-07-29; box width is terminal-dependent):

```
╭────────────────────────────────────────────────────────╮
│ ACE — Asymmetric Cognitive Equilibrium                 │
│ Topic: (preflight — no topic yet)                      │
│ Preset: architecture                                   │
│ Divergence: claude-sonnet-4-6 (agy) + cognitive frames │
│ Synthesis: claude-opus-4-8 (strength 4.0/5↗)           │
│ Cycles: 1 | Debt threshold: 2.5 | Budget: 4            │
╰────────────────────────────────────────────────────────╯
🧭 agy: available ✓ — divergence (lateral branches; live Google seat)
🔵 Claude: available ✓ — synthesis (trajectory maintenance)
```

Adding `--providers agy,ollama` instead prints `(agy, ollama)` on the divergence line plus a
`🟡 ollama: available ✓ — divergence` row. Do not paste one command's output under the other —
that is exactly the kind of mismatch that makes a reader distrust the engine.

A banner row is a `shutil.which` PATH lookup, **not** proof the seat can produce branches. The
`doctor.sh` line above is the part that actually exercises each seat.

## Step 2 — cheap first pass, no external seat, no quota (free)

Pick three or four frames from [frame-catalog.md](frame-catalog.md) and answer the question once
per frame as Claude, here in the conversation.

This is the correct cheap pass — **not** `--providers ollama`. A 7B local seat is a privacy tool,
not a debate peer; this topic is not privacy-bound, so there is nothing to buy by sending it to a
weaker model. If the frames all converge, treat that as a shared-blind-spot *suspicion*, not as
confirmation, and go to step 3.

## Step 3 — one cross-family probe (T3 — spends agy quota)

```bash tier=T3 verified=2026-07-29
printf '2\n' | /usr/local/bin/python3.11 -m ace.cli run \
  "SQLite R-tree vs Postgres PostGIS for the 360 frame index" \
  --preset architecture --cycles 1 --providers agy
```

The `printf` is mandatory, not decoration: with no tty the end-of-cycle `Focus` prompt raises
`Abort` and the cycle dies *after* the quota has been spent
(see [troubleshooting.md §9](troubleshooting.md)).

## Step 4 — read the routing line

- `regime: underdetermined` / `ambiguous` → you have not converged. Run another cycle before
  trusting the panel; synthesis here is secretly a second divergence.
- `regime: converging` → the panel is worth synthesizing.
- `↑ ESCALATE DIVERGENCE` → the shared-blind-spot alarm fired. `agy` is already spent, so the only
  remaining family is a manual `~/.claude/scripts/adapters/openai.sh "<prompt>"` probe (T3) —
  the engine cannot dispatch it for you.

## Step 5 — aggregate asymmetrically

Take only agy's *disagreements* to Claude:

> agy argued PostGIS because R-tree cannot index the ±180° yaw seam without a split box.
> That contradicts our design. Is the split-box workaround load-bearing or a hack?

Agreement from agy on everything else changes nothing — do not record it as confirmation, and
never write "agy concurred" in a summary.

## Step 6 — synthesize and hand off

Paste the synthesis panel into Claude Code and decide. State plainly that there was no rebuttal
round — the branches never saw each other. If the decision is now made, hand off to `/ACE:plan`
to turn it into ordered falsifiable steps.
