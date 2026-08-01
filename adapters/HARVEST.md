# Provider adapters — harvested contracts

Standalone, octopus-free provider adapters for the ACE stack. This directory is
the distilled result of the migration's **Harvest** phase (SPEC §2): it carries
forward the working provider-invocation knowledge from Claude-Octopus so that
`~/claude-octopus` and `~/.claude-octopus` can be deleted without losing months
of debugging.

**Every adapter depends on ZERO octopus code** (verified: no runtime reference to
`claude-octopus`, `orchestrate.sh`, `dispatch.sh`, `OCTOPUS_*`, etc. — only
provenance comments mention the origin).

Files:
- `agy.sh` — Antigravity / Gemini-family (research breadth, decorrelated debate voice)
- `ollama.sh` — local Qwen (GDPR/PII firewall, overnight bulk)
- `openai.sh` — OpenAI different-family second opinion
- `openai-compatible-agent.py` — harvested verbatim; stdlib-only agentic loop (tools + 429/5xx retries)

Common CLI: `<adapter>.sh "<prompt>"` (or prompt on stdin); `<adapter>.sh --health`
runs a zombie-safe sentinel (verifies real output, not mere binary presence).

---

## Live proof (2026-07-24, run with octopus still installed)

| Adapter | `--health` result | Notes |
|---|---|---|
| `ollama.sh` | ✅ `OLLAMA-OK (qwen2.5-coder:7b)` | real generate produced code; absent-model path failed CLOSED (exit 70, no auto-pull) |
| `agy.sh` | ✅ `AGY-OK (mode=argv)` in ~8s | **argv-vs-stdin spike RESOLVED: argv works on agy 1.1.4** (no stdin fallback needed) |
| `openai.sh` | ✅ `OPENAI-OK (key valid; 117 models)` | **API-key spike RESOLVED: key valid.** Initial 4×HTTP-500 was a transient OpenAI outage, not a dead key — status-aware health now distinguishes 401/429/5xx |

Both spikes the spec left owed are now closed positively. The OpenAI API-key path
is viable as the **primary** second-opinion seat (more debuggable than
`gpt-oss:120b-cloud`); `OPENAI_MODEL` defaults to `gpt-5` (verified on-account).

---

## agy — Antigravity (Gemini family)

- **Model:** Gemini-family, selected in agy's own `/model` UI (Gemini Flash today).
- **Auth:** Google OAuth; state at `~/.gemini/antigravity-cli/` — **outside** both
  octopus dirs, so it survives deletion. Not the `GEMINI_API_KEY` env var (vestigial).
- **Invocation (argv form, verified):**
  `agy -p "<prompt>" --sandbox --dangerously-skip-permissions --print-timeout 5m0s`
- **DO NOT pass `--model`.** The old octopus default (`Claude Sonnet … Thinking`)
  forced agy onto an exhaustible Claude/GPT quota group → **silent empty output**.
  Omitting it uses the working authed default.
- **Bounded exec:** macOS has no `timeout` binary — `agy.sh` bounds the call
  in-process (`_bounded`, default 120s on the health probe).
- **Health:** sentinel `Reply with exactly: AGY-OK`, content-match on `AGY-OK`
  (not non-emptiness — v1.1.6 could return plausible off-topic text = a worse zombie).
  **Re-run `--health` after every agy version bump** (the input contract has changed
  across versions before).

## ollama — local Qwen

- **FAIL CLOSED on absent models.** `ollama run <model>` silently auto-pulls; a
  provider-failure cascade once triggered a ~42 GB download unattended. `ollama.sh`
  confirms presence via `/api/tags` first and refuses (exit 70) with a pre-pull hint.
- **HTTP API, not CLI:** `POST /api/generate`, `stream:false`, `think:false`,
  `temperature:0`, capped `num_predict`. A "thinking" model can spend its whole
  budget on reasoning and return an **empty** response — treated as FAILURE.
- **Routing:** code → `qwen2.5-coder:7b`; bulk classify/extract → `qwen3:4b`;
  **nothing** to `qwen3:8b` (dominated on this CPU-only box).
- **`gpt-oss:120b-cloud` is CLOUD, not local** (verified TLS egress). Never route
  GDPR/PII data to it. It is the different-family cloud *fallback*, not a privacy seat.
- **Health:** `/api/tags` liveness + end-to-end tiny generate asserting non-empty response.

## openai — different-family second opinion

- **Value = decorrelated error** (a non-Claude training family). Only reason it exists.
- **Do NOT use the codex CLI:** quota-dead (exit 137), which never matched octopus's
  quota-watcher patterns → silent zombie. Use the API-key path.
- **Health = `GET /v1/models`:** validates the key AND lists usable model IDs in one
  cheap call — no model-guessing. **Status-aware:** 401/403 = key dead; 429 = quota
  (key still valid); 5xx = transient server error (key NOT disproven, retry); 000 = network.
- **Run:** one-shot `POST /chat/completions` by default; `--agent` routes to
  `openai-compatible-agent.py` for a full tool loop (edits files under cwd).
- **Key hygiene:** read from `$OPENAI_API_KEY` (or `$OPENAI_KEY_ENV`). Per SPEC §7,
  rotate it and move it out of `~/.claude/settings.json` into a secret store.

---

## Exit-gate test (octopus-renamed) — how to run it

The spec's Phase-2 exit gate proves there is no HIDDEN octopus dependency by
running the adapters with octopus renamed away:

```
mv ~/claude-octopus ~/claude-octopus.OFF && mv ~/.claude-octopus ~/.claude-octopus.OFF
~/.claude/scripts/adapters/ollama.sh --health   # expect OLLAMA-OK
~/.claude/scripts/adapters/agy.sh   --health    # expect AGY-OK
~/.claude/scripts/adapters/openai.sh --health   # expect OPENAI-OK (or a clean status)
mv ~/claude-octopus.OFF ~/claude-octopus && mv ~/.claude-octopus.OFF ~/.claude-octopus
```

**Not run automatically here on purpose:** while `~/.claude-octopus` is renamed,
the *live* SessionStart hooks (still pointing there until cutover) are momentarily
broken, so this must be done in one shell that renames back immediately, with no
other sessions starting meanwhile. The static grep already proves zero runtime
octopus references, so this test is belt-and-suspenders — run it during the
cutover window, not mid-workday.

## Deliberately dropped (simplicity)

- The capped-pull machinery (`ollama-pull-guard.lib.sh`, size caps, opt-in pull) —
  with a 3-model fleet, manual pre-pull is simpler than a guard framework. Fail closed.
- The 6-tier health library — replaced by one per-adapter sentinel check.
- `check-ollama-models.sh` staleness tracking — not needed for a hand-managed fleet.
