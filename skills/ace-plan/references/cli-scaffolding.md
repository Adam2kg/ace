# When the `ace` CLI is worth adding to a planning session

`/ACE:plan` does **not** require the `ace` CLI. Planning is synthesis; the CLI is a divergence
engine. This file covers the minority of cases where running it alongside a plan earns its
keep, and documents the flags that actually exist (verified against
`/Users/sebastianziegler/ace/ace/cli.py`, 2026-07-29).

Tier codes (T1/T3) are defined in `SKILL.md` § *Command verification*.

---

## The one case where it helps

`ace run` **always dispatches an external seat** — `--providers` defaults to `agy`
(`ace/cli.py:123`) and `diverge()` is called unconditionally (`ace/cli.py:293`); there is no
zero-provider mode (an all-unknown `--providers` list leaves `active == []` and
`ThreadPoolExecutor(max_workers=0)` raises `ValueError: max_workers must be greater than 0`).
Running it mid-draft therefore puts a second voice in the *drafting* seat, which `/ACE:plan`
forbids. So:

- **Do not run `ace run` while drafting a plan.** If you want the Governor framing, take the
  menu text, not the dispatch: `[3] Next step` asks for the next step "as a falsifiable claim"
  (`ace/cli.py:427–430`) — that prompt is reproduced in `SKILL.md` and needs no engine.
- **`ace debt --state-file <path>` is safe** (no dispatch): on multi-session plans, a branch
  with high attractor debt is usually the step you keep avoiding. This is the only CLI use
  `/ACE:plan` endorses.
- If you genuinely need divergence over an unordered step set, that is `/ACE:debate`'s job —
  say so and hand off, rather than smuggling a divergence run into a plan.

---

## Real commands and flags

All read from `ace/cli.py`. Do not invent flags — the ones below are the complete set for
`run`. They are documented so you can **read** an `ace run` invocation, not so you can fire one
mid-plan; see above.

| Flag | Meaning |
|---|---|
| `--mode h\|human\|a\|ai` | Root mode. `a`/`ai` = GOVERNOR (what planning uses). Omit and the CLI asks. |
| `--preset NAME` | One of `architecture`, `debugging`, `design-review`, `looping`, `frames-deep`, `frames-adversarial`, `human-adhd`, `human-scientific`, `human-creative`. Passing `--preset` implies the preset's own `mode`. |
| `--cycles N` | Diverge→synthesize cycles. Default 1. |
| `--providers a,b` | Divergence providers. Default `agy`. |
| `--state-file PATH` | Persist coupling state JSON. |
| `--human-mode` | Human is the primary divergence engine; suppresses convergence warnings. Not what planning wants. |
| `--synthesis-strength F` | Override 1.0–5.0. |
| `--divergence-model` / `--synthesis-model` | Model overrides. |
| `--budget N` | Override base interrupt budget. |
| `--debt-threshold F` | Override attractor-debt surface threshold. |
| `--coherence-floor F` | Drop branches below this coherence before synthesis. Useful on grounded engineering topics. |

Other subcommands: `ace banner --preset NAME` (preflight, no session), `ace debt --state-file
PATH`, and the `ace memory` group (`harvest`, `backfill`, `show`).

**There is no `ace status` subcommand** on this branch, despite older notes referring to one.

---

## Presets you would pass if you escalate to `/ACE:debate`

`/ACE:plan` itself dispatches nothing, so these matter only when you hand off. Only GOVERNOR
(`mode="ai"`) presets belong anywhere near planning work:

| Preset | Divergence → Synthesis | Strength | Use when planning… |
|---|---|---|---|
| `architecture` | sonnet-4-6 → opus-4-8 | 4.0 (dynamic) | new systems, migrations — the default |
| `debugging` | sonnet-4-6 → opus-4-8 | 3.0 | an incident remediation plan (follow one hypothesis deep) |
| `design-review` | haiku-4-5 → sonnet-4-6 | 2.0 | many small changes, consistency matters |
| `looping` | haiku-4-5 → sonnet-4-6 | 1.0 | repetitive batch work with no trajectory to protect |
| `frames-deep` | sonnet-4-6 → sonnet-4-6 | 3.0 | **⚠ does NOT suppress external dispatch on this branch** — `frames_only` only disables frame injection; `ace/cli.py:293` still dispatches `--providers` (default `agy`). Pass `--providers ollama` explicitly for the no-quota behaviour the preset advertises. See the defect box in `skills/ace-debate/SKILL.md`. |
| `frames-adversarial` | sonnet-4-6 → opus-4-8 | 4.0 | security / threat-model planning |

Values read live from `ace/presets.py` on 2026-07-29 via:

```bash tier=T1
# cd first: the import needs the repo root on sys.path, so this is cwd-dependent.
cd ~/ace && /usr/local/bin/python3.11 -c "from ace.presets import PRESETS; [print(k, v.mode, v.divergence_model, v.synthesis_model, v.synthesis_strength) for k,v in PRESETS.items()]"
```

---

## Warning: the installed CLI is stale

```bash tier=T1
# T1 — executed 2026-07-29
ace --help
```
```
Commands:
  debt  Show attractor debt from a saved coupling state.
  run   Run an ACE session on TOPIC.
```

`/usr/local/bin/ace` predates this branch: no `banner`, no `memory`. To use the current engine,
run it from the repo instead:

```bash tier=T1
# T1 — executed 2026-07-29, prints the coupling banner + live provider rows
cd /Users/sebastianziegler/ace && /usr/local/bin/python3.11 -m ace.cli banner --preset architecture --providers agy
```
```
╭──────────────────────────────────────────────────────────────────────────────╮
│ ACE — Asymmetric Cognitive Equilibrium                                       │
│ Topic: (preflight — no topic yet)                                            │
│ Preset: architecture                                                         │
│ Divergence: claude-sonnet-4-6 (agy) + cognitive frames                       │
│ Synthesis: claude-opus-4-8 (strength 4.0/5↗)                                 │
│ Cycles: 1 | Debt threshold: 2.5 | Budget: 4                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
🧭 agy: available ✓ — divergence (lateral branches; live Google seat)
🔵 Claude: available ✓ — synthesis (trajectory maintenance)
```

Note `ace banner` checks provider availability with a PATH lookup (`shutil.which`) only — that
is a presence check, **not** a zombie-safe health check. For real health use `/ACE:doctor`.

**Re-verify:** `ace --help` and `python3.11 -m ace.cli --help`. If the two now agree, the
global binary has been reinstalled and this warning can be deleted.
