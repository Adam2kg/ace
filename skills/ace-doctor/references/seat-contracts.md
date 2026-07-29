# Seat contracts — the long tail behind /ACE:doctor

Per-seat invocation contracts, environment variables, and exclusion history.
Source of truth: `~/.claude/scripts/adapters/*.sh` and their `HARVEST.md`.
Read `../SKILL.md` first; this file is reference only.

All adapters share one CLI shape:

```
<adapter>.sh "<prompt>"     # prompt as argv
<adapter>.sh                # prompt on stdin
<adapter>.sh --health       # zombie-safe sentinel (also accepts --probe)
```

---

## agy — Antigravity (Gemini family)

**Role:** research breadth and a decorrelated debate voice. Its grounding probe passed an
independent check on 2026-07-29: asked to fetch `api.github.com/repos/ollama/ollama/releases/latest`
it returned `v0.32.5`, matching an independent fetch exactly — it genuinely fetches live
sources rather than reciting training recall.

**Invocation (argv form, the default):**

```
agy -p "<prompt>" --sandbox --dangerously-skip-permissions --print-timeout 5m0s
```

**Stdin form (fallback, used by older versions):**

```
printf %s "<prompt>" | agy --print --sandbox --dangerously-skip-permissions --print-timeout 5m0s
```

`--health` tries argv first, then stdin, and reports which one worked (`mode=argv` /
`mode=stdin`). That report is the live answer to the argv-vs-stdin question on this box —
re-read it after every agy upgrade.

**Hard rule: never pass `--model`.** The old Claude-Octopus default
(`Claude Sonnet … Thinking`) forced agy onto an exhaustible Claude/GPT quota group and
produced **silent empty output**. Omitting it uses the model selected in agy's own `/model`
UI (Gemini Flash today), on the working authed default.

**Auth:** Google OAuth, state in `~/.gemini/antigravity-cli/` — outside every octopus
directory, so it survived the octopus deletion. `GEMINI_API_KEY` is vestigial; it is not
what authenticates this seat.

**Bounded exec:** macOS ships no `timeout` binary, so `agy.sh` bounds the call in-process.
`_bounded` returns 124 on timeout, **but the health path discards that status** — it is
called inside a command substitution, so `health()` falls through to the stdin form and
returns 1. See the exit-code table in `../SKILL.md`. Health default
`AGY_HEALTH_TIMEOUT=120` seconds, tried twice (argv then stdin), so a genuine timeout costs
~240s. The `run` path (`_run`/`_run_argv`/`_run_stdin`) does not use `_bounded` at all — it
relies on agy's own `--print-timeout`.

**Env:** `AGY_BIN`, `AGY_INPUT_MODE=argv|stdin`, `AGY_PRINT_TIMEOUT=5m0s`,
`AGY_HEALTH_TIMEOUT=120`.

**Binary resolution order:** `$AGY_BIN` → `command -v agy` → `~/.local/bin/agy` → literal
`agy`. On this box it resolves to `/Users/sebastianziegler/.local/bin/agy` (2026-07-29).

---

## ollama — local Qwen

**Role:** the privacy seat (PII/GDPR never leaves the box) and the bulk seat. **Never a
debate peer** — frames on a frontier model beat Claude-vs-7B on every axis; a local 7B
"defers from incapacity, not judgment", which the coupling function cannot distinguish
from genuine agreement.

**Transport:** HTTP `POST /api/generate` with `stream:false`, `think:false`,
`temperature:0`, capped `num_predict`. The CLI path is not used — it gives dirty status
and parse behaviour.

**Fail-closed rule:** `ollama run <model>` silently auto-pulls a missing model. A
provider-failure cascade once triggered an unattended **~42 GB** download. `ollama.sh`
therefore confirms presence via `/api/tags` *before* generating, and refuses otherwise:

- `run` with an absent model → exit **70**, message `FAIL CLOSED (no auto-pull)`
- `--health` with an absent model → exit **1**
- server unreachable (either path) → exit **69**

Never re-introduce an auto-pull, a size cap, or an "opt-in pull" framework. Manual pre-pull
is the design.

**Routing:** code → `qwen2.5-coder:7b`; bulk classify/extract → `qwen3:4b`; **nothing** to
`qwen3:8b` (dominated on this CPU-only box).

**`gpt-oss:120b-cloud` is CLOUD**, not local (verified TLS egress) despite being listed by
`ollama list`. It is the different-family cloud *fallback*. Never route GDPR/PII to it.

**This is a rule, not an enforced invariant.** `_ollama_model()`
(`ace/agents/divergence.py:142`) returns `out[1].split()[0]` — the first row of
`ollama list` — whenever `ACE_OLLAMA_MODEL` / `OCTOPUS_OLLAMA_MODEL` are unset. `ollama
list` sorts by MODIFIED and nothing pins the ordering; `gpt-oss:120b-cloud` is a row in
that list (it sorts last on 2026-07-29, but only incidentally). Pin the model before any
privacy-bound run: `export ACE_OLLAMA_MODEL=qwen2.5-coder:7b`. *Open defect: make the
selector an allowlist.*

**Sentinel drift returns 0.** `health()` (`ollama.sh:80-84`) content-matches `OLLAMA-OK`,
but on a MISS it prints `OLLAMA-OK (<m>; alive, sentinel drift: …)` and still returns 0 —
so `doctor.sh` renders `ollama ✅` and `ALL SEATS HEALTHY`. agy is strict by contrast (any
non-`AGY-OK` output → exit 1). Also note `--health` probes `$OLLAMA_MODEL`, which is not
necessarily the model `_ollama_model()` will select for divergence.

**Empty response = failure.** A thinking model can spend its entire token budget narrating
reasoning and return an empty `.response`. That is the local incarnation of the zombie.

**Env:** `OLLAMA_URL=http://localhost:11434`, `OLLAMA_MODEL=qwen2.5-coder:7b`,
`OLLAMA_NUM_PREDICT=512`, `OLLAMA_TIMEOUT=120`. The divergence runner overrides
`OLLAMA_NUM_PREDICT=1024` for branch generation.

---

## openai — different-family second opinion

**Role and only justification:** decorrelated error. A non-Claude training family. It buys
nothing else, and its *agreement* is worth nothing (see the asymmetric-aggregation rule in
the debate skill) — only its *disagreement* is a signal.

**Health = `GET /v1/models`.** One cheap call validates the key *and* enumerates usable
model ids, so no model-guessing is required. Status-aware by design:

| HTTP | Meaning | Exit |
|---|---|---|
| 200 with models | Key valid | 0 |
| 200 with zero models | Unavailable | 1 |
| 401 / 403 | Key dead — rotate | 1 |
| 429 | Quota — **key still valid** | 3 |
| 5xx | Transient server error — **key NOT disproven** | 4 |
| 000 / empty | Network unreachable | 5 |
| other | Unavailable | 1 |

The 401-vs-5xx distinction is the zombie gate applied to our own health check. It was
earned live: four consecutive HTTP 500s looked exactly like a dead key and were in fact an
OpenAI outage — the same key later listed 119 models.

**Run modes:** default is a one-shot `POST /chat/completions` (what a second opinion
needs). `--agent` routes to `openai-compatible-agent.py`, a stdlib-only agentic loop with
tool use and 429/5xx retries that **edits files under `$PWD`** — do not invoke it for a
health question.

**Env:** `OPENAI_API_KEY` (or point `OPENAI_KEY_ENV` at another var name),
`OPENAI_BASE_URL=https://api.openai.com/v1`, `OPENAI_MODEL` (default `gpt-5`),
`OPENAI_TIMEOUT=60`.

**Key hygiene (open item):** the key should be rotated out of `~/.claude/settings.json`
into a secret store.

---

## Excluded seats — why they are gone and stay gone

**codex — permanently excluded.** Quota-dead: it exits **137** (SIGKILL-shaped), and 137
never matched the old quota-watcher's stderr patterns, so the failure was invisible and the
seat read as healthy. It is the canonical zombie. The binary is *still installed* at
`/usr/local/bin/codex` (2026-07-29), which is exactly why `shutil.which`-style checks are
banned as health checks. `_run_codex` was deleted from `ace/agents/divergence.py`; the
OpenAI API-key path replaces it.

**gemini CLI — retired.** Superseded by agy for the Gemini family. `_run_gemini` was
deleted. `ace/cli.py` still carries a legacy `_PROVIDER_ROWS` entry labelling it
"deprecated, superseded by agy"; it is a display label with no runner behind it. Asking for
`--providers gemini` yields no seat, because `diverge()` filters the requested list against
`runners = {"agy": ..., "ollama": ...}`.

---

## Exit-gate test (run during a cutover window, not mid-workday)

Proves no hidden Claude-Octopus dependency by running the adapters with octopus renamed
away. **T2/T3 — mutating (renames directories) and it momentarily breaks live SessionStart
hooks.** Run it in a single shell that renames back immediately, with no other sessions
starting:

```bash tier=T3 verified=2026-07-29
mv ~/claude-octopus ~/claude-octopus.OFF && mv ~/.claude-octopus ~/.claude-octopus.OFF
~/.claude/scripts/adapters/ollama.sh --health   # expect OLLAMA-OK
~/.claude/scripts/adapters/agy.sh   --health    # expect AGY-OK
~/.claude/scripts/adapters/openai.sh --health   # expect OPENAI-OK (or a clean status)
mv ~/claude-octopus.OFF ~/claude-octopus && mv ~/.claude-octopus.OFF ~/.claude-octopus
```

A static grep already proves zero runtime octopus references in the adapters, so this is
belt-and-suspenders.

---

## Deliberately dropped machinery (do not rebuild)

- The capped-pull framework (`ollama-pull-guard.lib.sh`, size caps, opt-in pull) — with a
  3-model fleet, manual pre-pull is simpler. Fail closed instead.
- The 6-tier health library — replaced by one per-adapter sentinel.
- `check-ollama-models.sh` staleness tracking — unnecessary for a hand-managed fleet.
