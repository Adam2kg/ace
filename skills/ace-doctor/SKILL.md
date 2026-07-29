---
name: ace-doctor
description: >-
  Check whether the ACE provider seats (agy, ollama, openai) are actually alive before
  running a debate, a plan, or any multi-provider work — and diagnose them when they are
  not. Use for "run ACE doctor", "are my providers healthy", "ACE preflight", "check seat
  health", "which providers are up", "why did agy return nothing", "ollama says model not
  present", "is my OpenAI key dead / I got a 500", "provider says available but produced
  no output", "ACE isn't working", "ace run produced nothing", "my debate round came back
  empty — is a seat dead?", "ace says a provider is available but I got no branches",
  "ACE ran but the output looks like an error dump". Also the FIRST stop whenever an ACE
  run produced no output, empty branches, or output that looks like an error dump — a
  zombie seat is the most common cause, and no other ACE skill can diagnose it. Checks the
  ACE adapter seats under ~/.claude/scripts/adapters/ (agy, ollama, openai) — not the
  retired Octopus provider fleet. If /octo:preflight or /octo:skill-doctor are still
  installed they will also match "check provider health"; those report on providers ACE no
  longer uses. This is a HEALTH CHECK only — it never runs a debate (use /ACE:debate) and
  never produces a plan (use /ACE:plan). Verified 2026-07-29.
---

# /ACE:doctor — is the fleet actually alive?

One command, all seats, once per session. `doctor.sh` prefers each seat's **real
invocation** with a **content-matched sentinel** over binary presence. Two rows are
deliberate exceptions and are labelled as such below: **openai** is probed by key/catalog
validity (`GET /v1/models`), not by a completion; **handoff** is not a provider and is
checked by parse.

**Vocabulary (defined once):**

- **Seat** — one provider slot in the ACE fleet (agy, ollama, openai). A seat is a role,
  not a binary.
- **Zombie seat** — a seat that reports healthy but delivers nothing usable: the binary is
  on `$PATH`, the process exits, a file gets written — and the content is empty, an error
  dump, or off-topic. See "The zombie gate" below.
- **Sentinel** — a fixed string the health probe asks the seat to echo back
  (`AGY-OK`, `OLLAMA-OK`). Content-matching the sentinel is what separates a live seat
  from a zombie.
- **Fail closed** — on ambiguity, refuse and report, rather than proceeding with a
  plausible-looking substitute.

---

## When to use this — and when not to

| Situation | Command |
|---|---|
| Start of a session that will use external providers | `/ACE:doctor` |
| A seat came back empty / a debate round looks wrong | `/ACE:doctor` |
| You want multiple independent takes on a question | `/ACE:debate` |
| You want one converged, sequenced plan | `/ACE:plan` |
| You want the coupling engine's own session banner | `ace banner --preset <p>` (see the trap below) |

**Do not use `/ACE:doctor` to answer a question.** It runs no divergence, no synthesis, no
frames. It answers exactly one question: *which seats can be trusted right now?*

---

## The seats and what health actually proves

| Seat | What it is | Health probe | What a ✅ proves | What it does NOT prove |
|---|---|---|---|---|
| **agy** | Antigravity CLI, Gemini-family. The research-breadth seat. Google OAuth state in `~/.gemini/antigravity-cli/`. | argv sentinel `Reply with exactly: AGY-OK`, content-matched; falls back to the stdin form and reports which mode worked | OAuth live, quota group not exhausted, argv-vs-stdin contract still holds on this version | Nothing about answer quality or long prompts — see caveat **[A]** |
| **ollama** | Local Qwen. The privacy seat (GDPR/PII stays on the box) and the bulk seat. | `/api/tags` liveness + tiny generate asserting a non-empty response | Server up, the *named model* is present, and generation returns text | That the model is any good — see caveat **[O]** |
| **openai** | Different-training-family second opinion. Exists only for **decorrelated error**. *Exception to the real-invocation rule.* | `GET /v1/models`, status-aware — key/catalog validity, *not* `POST /chat/completions` | The key is valid and the account can see N models | That any model id will accept your request — see caveat **[X]** |
| **handoff** | Not a provider — `~/.claude/scripts/handoff-v2.sh`. A migration precondition. *Exception to the real-invocation rule.* | executable bit + `bash -n` parse | The script exists and parses | That it runs correctly |

**[A] — a green agy is *availability*, not orthogonality.** The sentinel is one line; it
says nothing about long or structured prompts. And see the epistemic note below.

**[O] — the ollama ✅ has two blind spots.** A drifted sentinel still returns 0 (see the
zombie gate below). And it proves nothing about the model *divergence* will pick: health
probes `$OLLAMA_MODEL`, divergence calls `_ollama_model()`.

**[X] — a green openai is not a dispatchable seat.** There is no `_run_openai`;
`runners = {agy, ollama}` (`ace/agents/divergence.py:339`). openai is reachable **only** via
`~/.claude/scripts/adapters/openai.sh` as a manual second opinion — `--providers openai` is
filtered out by `diverge()` and leaves an empty active list.

**`gpt-oss:120b-cloud` is CLOUD despite living in ollama** — never the privacy seat; see
Graceful degradation below. ACE does **not** structurally prevent routing to it:
`_ollama_model()` (`ace/agents/divergence.py:142`) defaults to the **first row of
`ollama list`** when no override is set, and that ordering is not pinned. **Before any
privacy-bound run, pin the model explicitly:**

```bash tier=T1
export ACE_OLLAMA_MODEL=qwen2.5-coder:7b
echo "ACE_OLLAMA_MODEL=$ACE_OLLAMA_MODEL"   # echo back: an export alone proves nothing
```

*Open defect: the selector should be an allowlist, not "whatever sorts first".*

**Epistemic note on [A].** Frames decorrelate the question-space explored, not the error
distribution, and cross-family orthogonality among frontier models is modest (~15–25pp) —
so on high-stakes items fire a cross-family probe regardless of what the agreement signal
says. See `/ACE:debate`.

**Permanently excluded seats:** `codex` (quota-dead, exits 137 — a code that never matched
the old quota-watcher's stderr patterns, so it failed *silently*) and the `gemini` CLI
(retired). Neither appears in the engine's runners; `ace/agents/divergence.py` ships exactly
two, `{"agy": _run_agy, "ollama": _run_ollama}`. Note `codex` is still on `$PATH` at
`/usr/local/bin/codex` — presence proves nothing.

---

## The zombie gate (the governing concept)

> A seat that passes `command -v` but returns empty or off-topic output provides **zero
> value while reporting healthy** — and its vacuous "agreement" gets miscounted as
> concurrence in aggregation.

**Real on-disk exhibit:** a debate round file that was **byte-identical to a `.err` file**
containing a Gemini `IneligibleTierError` stack trace — filed as a debate round. Every
naive gate passed on it: the file existed, it was non-empty, it was larger than 500 bytes.
The debate then "aggregated" a stack trace as a peer opinion.

Therefore, in ACE:

1. **Presence checks are banned as *provider* health checks.** `command -v`, `test -f`,
   `size > N`, and exit-0 are all necessary-not-sufficient. (`handoff` is not a provider —
   it is checked by parse, and labelled as an exception in the table above.)
2. **Every gate verifies on-topic output** — sentinel content match, or a parse that would
   fail on an error dump. **One asymmetry on this fleet:** agy content-matches strictly
   (any non-`AGY-OK` output → ❌, exit 1), but `ollama.sh --health` downgrades a sentinel
   miss to `OLLAMA-OK (<m>; alive, sentinel drift: …)` and still exits 0, so `doctor.sh`
   prints `ollama ✅`. **Read the parenthetical, not just the tick** — `sentinel drift`
   means generation works but instruction-following is unproven.
3. **The runners enforce it too.** `_run_agy` / `_run_ollama` return
   `DivergenceResult(available=False)` on empty output *or* non-zero exit, so a
   silently-empty seat is reported as down, never as a healthy seat with zero branches.

### Trap: `ace banner` availability rows are presence-only

`ace/cli.py::_print_provider_rows` uses `shutil.which(provider)`. That is a **PATH lookup**.
It prints `available ✓` for a binary whose OAuth is dead, whose quota is gone, or — for
ollama — whose server is not running. It is a UI convenience, not a health check.

**Rule: `ace banner` tells you what is installed. `/ACE:doctor` tells you what works.**
When they disagree, doctor wins.

---

## Run it

**Default — the free path:**

```bash tier=T3 verified=2026-07-29
# T1 (read-only, free) — skips agy only. Issues just /api/tags + a 16-token local
# generate + GET /v1/models. Use before local/bulk work.
~/.claude/scripts/adapters/doctor.sh --fast
```

Real output — `--fast`, executed 2026-07-29 21:20, exit 0:

```
ACE provider health — 2026-07-29 21:20
─────────────────────────────────────────────
ollama   ✅ OLLAMA-OK (qwen2.5-coder:7b)
openai   ✅ OPENAI-OK (key valid; 119 models available)
agy      ⏭  skipped (--fast)
handoff  ✅ handoff-v2.sh present + parses
─────────────────────────────────────────────
ALL SEATS HEALTHY
```

> ⚠️ **`--fast` still prints `ALL SEATS HEALTHY`.** That line means *every **checked** seat
> is healthy*. A skipped seat is **unknown, not up**. Never enter a debate or any
> agy-dependent work on the strength of a `--fast` pass — re-run without `--fast` first.

**Full check — spends quota:**

```bash tier=T3 verified=2026-07-29
# T3 — exercises the PAID/OAuth agy seat (~10s). Correct to run once per session;
# do not loop it. Use --fast when you only need the local + openai picture.
~/.claude/scripts/adapters/doctor.sh
```

Real output — full run, `verified: manual 2026-07-29` (agy is a paid/OAuth seat; do not
re-run it casually), exit 0:

```
ACE provider health — 2026-07-29 20:43
─────────────────────────────────────────────
ollama   ✅ OLLAMA-OK (qwen2.5-coder:7b)
openai   ✅ OPENAI-OK (key valid; 119 models available)
agy      ✅ AGY-OK (mode=argv)
handoff  ✅ handoff-v2.sh present + parses
─────────────────────────────────────────────
ALL SEATS HEALTHY
```

Per-seat probes, when you need to isolate one:

```bash tier=T1
# T1  — free, local
~/.claude/scripts/adapters/ollama.sh --health          # → OLLAMA-OK (qwen2.5-coder:7b)
# T1  — catalog read on a paid key, no completion, no tokens. This is what --fast runs.
~/.claude/scripts/adapters/openai.sh --health          # → OPENAI-OK (key valid; 119 models available)
# T3  — spends agy OAuth quota; verified: manual 2026-07-29. Do not loop.
~/.claude/scripts/adapters/agy.sh    --health          # → AGY-OK (mode=argv)   [~8s]
```

---

## Symptom → diagnosis → fix

| Symptom | Diagnosis | Fix |
|---|---|---|
| `agy ❌ UNAVAILABLE — no AGY-OK from either input mode` | OAuth expired, quota group exhausted, or the model picked in agy's `/model` UI is not on a free tier. **Can also be a timeout** — see the exit-code note on 124 | Re-auth agy; check `~/.gemini/antigravity-cli/`; reset the model in agy's own `/model` UI. **Never add `--model`** — see `references/seat-contracts.md` § agy |
| `AGY-OK (mode=stdin)` after a version bump | The argv input contract changed on this agy version; the adapter fell back | Nothing to fix immediately — the fallback works. Re-run `--health` after *every* agy version bump; the input contract has changed across versions before |
| agy returns text that is not `AGY-OK` | agy v1.1.6-class behaviour: plausible off-topic output — the worst zombie class | Health correctly reports ❌. Treat the seat as down; do not "eyeball" its output into a pass |
| `ollama ❌ server unreachable at http://localhost:11434` (exit 69) | ollama daemon not running | `ollama serve` |
| `ollama ❌ model '<m>' absent` (health, exit 1) / `not present — FAIL CLOSED` (run, exit 70) | Model not installed. **Auto-pull is banned** | `ollama pull <model>`. Never wire an automatic pull — see `references/seat-contracts.md` § ollama for the incident |
| `ollama: EMPTY response ... (thinking may have consumed the budget)` | A thinking model spent its whole `num_predict` narrating reasoning and returned nothing | The adapter already sends `think:false` + `temperature:0`; raise `OLLAMA_NUM_PREDICT`, or route to `qwen2.5-coder:7b` (code) / `qwen3:4b` (bulk). Empty is a FAILURE, never an answer |
| `OLLAMA-OK (<m>; alive, sentinel drift: ...)` — still renders `ollama ✅` + `ALL SEATS HEALTHY` | Generated text, did not echo the sentinel (`ollama.sh:80-84`). Exit still **0** | Partial pass: generation works, instruction-following is weak. Fine for bulk extraction; treat as **down** for structured work |
| `openai ❌ KEY DEAD (HTTP 401/403)` | Key revoked or wrong | Rotate the key in `$OPENAI_API_KEY` (or whatever `OPENAI_KEY_ENV` names) |
| `openai ⚠️ RATE-LIMITED / quota (HTTP 429)` | Quota — **the key is still valid** | Wait and retry. Do not rotate the key |
| `openai ⚠️ OPENAI SERVER ERROR (HTTP 5xx)` | Transient OpenAI outage. **A 500 does NOT mean the key is dead** | Retry later. Do not rotate, do not "fix" anything. (A live four-500 outage is documented in `references/seat-contracts.md` § openai) |
| `openai ❌ NETWORK unreachable (no HTTP status)` | No egress | Check the network; this says nothing about the key |
| `handoff ❌ missing or unparseable` | `~/.claude/scripts/handoff-v2.sh` absent or has a syntax error | Restore it; `bash -n` it before relying on a handoff |
| Everything reports healthy but a debate round is garbage | Zombie you have not caught yet | Open the round file. If it is a stack trace, an `.err` dump, or off-topic prose, discard the round and re-run doctor. Report it — the gate needs a new content assertion |

---

## Graceful degradation

When a seat is down, do not silently continue as if the fleet were whole.

| Condition | Rule |
|---|---|
| An external seat is down | **Degrade to frames-on-Claude, not to nothing.** Frames are ACE's default diversity mechanism; the external seat is the escalation path, not the baseline. Say explicitly which seat is missing and that only cross-family error-decorrelation was lost |
| The task is **PRIVACY-bound** (PII / GDPR) and ollama is down | **STOP. Fail closed.** Never fall back to a cloud seat — that includes `gpt-oss:120b-cloud`, which is cloud despite living in ollama. No degraded path exists here. And before any privacy-bound run that *does* proceed, pin the model: `export ACE_OLLAMA_MODEL=qwen2.5-coder:7b` — the default selector takes the first row of `ollama list` |
| No different-family seat is healthy (both agy and openai down) | Disclose: **"no independent second opinion available."** Claude reviewing its own output is not decorrelation. Note openai's second opinion is a **manual adapter call**, not an `ace run` seat |
| A seat is up but its output failed the content check | Treat it as **down**, not as agreement. Vacuous agreement is the specific failure the zombie gate exists to prevent |

---

## Exit codes

**`doctor.sh` returns only 0 or 1.** 0 = every *checked* seat healthy · 1 = at least one
seat unhealthy. openai 429/5xx render as ⚠️ and do **not** set the failure bit — the key is
not disproven. (Verified: `doctor.sh` ends in `exit "$FAIL"`, and `FAIL` is only ever 0
or 1.)

⚠️ Exit 0 is **not** unconditional good news. It is also returned when agy was
`⏭ skipped (--fast)` and when ollama returned `sentinel drift`. Read the rows.

### Per-adapter exit codes

The individual `*.sh` scripts are richer; doctor collapses all of these into its own 0/1.
Use these when you invoke a seat directly.

| Code | Seat | Meaning | Action |
|---|---|---|---|
| 0 | all | Healthy | Proceed |
| 1 | agy / ollama / openai | Seat unavailable (no sentinel; model absent; key dead) | See the symptom table |
| 2 | openai | `$OPENAI_API_KEY` not set | Export the key |
| 3 | openai | 429 quota — key valid | Retry later |
| 4 | openai | 5xx — key **not** disproven | Retry later |
| 5 | openai | Network unreachable | Check egress |
| 69 | ollama / agy / openai | Precondition missing: ollama server unreachable, agy binary not found, or `curl`/`jq` absent | Start the server / install the tool |
| 70 | ollama (`run` only) | Model absent — **fail closed, no auto-pull** | `ollama pull <model>` deliberately |
| 124 | agy | **Not currently reachable** — see the note below | Do not test for it |

> **The missing 124.** `_bounded` returns 124 on the wall-clock bound, but `agy.sh`'s
> `health()` calls it inside a command substitution (`out="$(_bounded …)"`), never tests the
> status, falls through to the stdin form, and ends at `return 1`. The `run` path does not
> use `_bounded` at all. So `agy.sh --health` can only ever exit **0, 1, or 69**, and a
> genuine timeout is indistinguishable *by exit code* from dead auth — which the symptom
> table would route to a pointless re-auth. **The tell is duration:** a real timeout takes
> ~2 × `AGY_HEALTH_TIMEOUT` (default 120s, tried twice → ~240s); dead auth fails fast. If
> `--health` hung for minutes before ❌, raise `AGY_HEALTH_TIMEOUT` — do not re-auth.

Long tail — per-seat invocation contracts, env vars, and the exclusion history for codex
and gemini: `references/seat-contracts.md`.

---

## Limitations (stated plainly)

- Health is a **point-in-time** claim. A seat can die between doctor and dispatch; the
  runners' own zombie gate is the second line of defence, not this command.
- The sentinel is a one-line prompt. A seat can pass `--health` and still fail on a long or
  structured prompt.
- `--fast` skips agy only. openai's `GET /v1/models` still runs (cheap, no completion).
  **It still prints `ALL SEATS HEALTHY`** with agy at `⏭ skipped` — unknown is not up.
- **Sentinel drift still renders ✅.** `ollama.sh` returns 0 when the model generates text
  but does not echo `OLLAMA-OK` (`ollama.sh:80-84`), so `doctor.sh` prints `ollama ✅` and
  still concludes `ALL SEATS HEALTHY`. **Read the row text, not just the summary line** —
  if it contains `sentinel drift:`, instruction-following is weak: usable for bulk
  extraction, not for anything where output shape matters, and per the degradation rule it
  should be treated as down for structured work. *Open defect: drift should set the failure
  bit or render ⚠️.*
- doctor checks the seats the *adapters* expose. It does not check Claude itself, the
  `ace` CLI install, or the Python environment.

---

## Provenance and maintenance

| Fact | Date verified | Tier | Re-verify with |
|---|---|---|---|
| doctor.sh `--fast` output, exit 0 (21:20) | 2026-07-29 | T1 | `~/.claude/scripts/adapters/doctor.sh --fast` |
| Full doctor.sh output incl. agy | 2026-07-29 | T3 (manual — spends agy quota) | `~/.claude/scripts/adapters/doctor.sh` |
| agy `--health` can only exit 0/1/69 (124 unreachable) | 2026-07-29 | T1 | `grep -n '_bounded' ~/.claude/scripts/adapters/agy.sh` — both call sites are command substitutions; the status is discarded |
| `_ollama_model()` defaults to first row of `ollama list` | 2026-07-29 | T1 | `grep -n 'out\[1\]' ace/agents/divergence.py` |
| doctor.sh exits only 0 or 1 | 2026-07-29 | T1 | `grep -n 'exit "\$FAIL"' ~/.claude/scripts/adapters/doctor.sh` |
| `OLLAMA-OK (qwen2.5-coder:7b)` | 2026-07-29 | T1 | `~/.claude/scripts/adapters/ollama.sh --health` |
| ollama absent-model: health→1, run→70 | 2026-07-29 | T1 | `~/.claude/scripts/adapters/ollama.sh --health this-model-does-not-exist:99b` |
| ollama server-down → 69 | 2026-07-29 | T1 | `OLLAMA_URL=http://localhost:9 ~/.claude/scripts/adapters/ollama.sh --health` |
| `AGY-OK (mode=argv)` | 2026-07-29 | T3 (manual) | `~/.claude/scripts/adapters/agy.sh --health` — **re-run after every agy version bump** |
| `OPENAI-OK (key valid; 119 models available)` | 2026-07-29 | T1 (catalog read, no tokens) | `~/.claude/scripts/adapters/openai.sh --health` |
| Local model fleet (coder:7b, qwen3:4b, qwen3:8b, gpt-oss:120b-cloud) | 2026-07-29 | T1 | `ollama list` |
| Engine ships exactly two runners | 2026-07-29 | T1 | `grep -n 'runners: dict' ace/agents/divergence.py` |
| `ace banner` rows are `shutil.which` presence-only | 2026-07-29 | T1 | `grep -n 'shutil.which' ace/cli.py` |
| `codex` still on `$PATH` (zombie exhibit) | 2026-07-29 | T1 | `command -v codex` |

Volatile: model ids, the OpenAI model count, and the agy input-mode contract. Everything
else in this skill is structural.
