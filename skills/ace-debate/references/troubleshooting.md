# /ACE:debate — extended troubleshooting chronicles

The short triage table lives in `../SKILL.md`. This file carries the *why* — the incidents that
produced each guard rail, so nobody removes one thinking it is paranoia.

All dates 2026 unless noted.

---

## 1. The zombie-gate incident (the founding lesson)

**Symptom:** a debate produced a full round file. It was non-empty, over 500 bytes, well-formed on
disk. It was also **byte-identical to the corresponding `.err` file**, which contained a Gemini
`IneligibleTierError` stack trace. The stack trace had been filed as a debate round and counted as
a participating voice.

**Why every obvious check missed it:**

| Check | Result on the poisoned file |
|---|---|
| `test -f` | pass |
| `test -s` (non-empty) | pass |
| `size > 500B` | pass |
| `command -v <provider>` | pass |

**The rule that came out of it:** *every gate must verify actual ON-TOPIC output.* Not existence,
not size, not exit code alone. This is why `agy.sh --health` content-matches on the literal string
`AGY-OK` rather than checking non-emptiness — agy v1.1.6 could return plausible *off-topic* text,
which is a strictly worse zombie than an empty response because it survives every emptiness check.

**Where it is enforced now:** `_run_agy` and `_run_ollama` in `ace/agents/divergence.py` both
return `DivergenceResult(available=False)` on `returncode != 0 or not raw`. There is no code path
that yields a silently-empty healthy seat.

**Residual hole:** a seat that returns non-empty *prose* passes the gate but yields zero branches,
because `_parse_branches` only accepts lines beginning with a digit, `-`, `*`, or `•` with more
than 10 characters of content. The seat then shows as available with 0 branches. Watch for that
shape explicitly.

---

## 2. The agy `--model` quota-group incident

**Symptom:** agy returned silent empty output. Not an error — empty.

**Cause:** the inherited Octopus invocation passed `--model "Claude Sonnet … Thinking"`. That
selection pushed agy onto an **exhaustible** Claude/GPT quota group rather than its authed default.
Once exhausted, the group returned nothing rather than an error.

**Fix, now baked into `agy.sh`:** never pass `--model`. The verified invocation is

```
agy -p "<prompt>" --sandbox --dangerously-skip-permissions --print-timeout 5m0s
```

**Auth:** Google OAuth, state at `~/.gemini/antigravity-cli/` — deliberately *outside* both Octopus
directories so it survived their deletion. `GEMINI_API_KEY` is vestigial and unused.

**Standing maintenance rule:** re-run `agy.sh --health` after **every** agy version bump. The input
contract has changed across versions before, and the failure mode is a silent zombie, not a crash.

---

## 3. The ~42 GB unattended download (why ollama fails closed)

**Symptom:** a provider-failure cascade caused `ollama run <model>` to be called with a model that
was not present locally. `ollama run` silently auto-pulls. Roughly 42 GB downloaded unattended.

**Fix:** `ollama.sh` confirms model presence via `/api/tags` **first** and refuses with exit 70 and
a pre-pull hint. It never pulls.

```
$ ~/.claude/scripts/adapters/ollama.sh "hi" "this-model-does-not-exist:99b"
ollama: model 'this-model-does-not-exist:99b' not present — FAIL CLOSED (no auto-pull). Pre-pull:  ollama pull this-model-does-not-exist:99b
(exit 70)
```
(verified: manual 2026-07-29)

**Related:** the adapter uses the HTTP API (`POST /api/generate`) with `stream:false`,
`think:false`, `temperature:0`, and a capped `num_predict`. A "thinking" model left unconstrained
can spend its entire token budget on reasoning and return an **empty** completion — treated as
FAILURE, not as a quiet success.

**Routing:** code → `qwen2.5-coder:7b`; bulk classify/extract → `qwen3:4b`; **nothing** to
`qwen3:8b` (dominated on this CPU-only box).

**Privacy trap:** `gpt-oss:120b-cloud` lives in ollama but is **cloud** (verified TLS egress).
It is a different-family cloud *fallback*, never a privacy seat. Never route GDPR/PII to it.

---

## 4. codex, exit 137 — the failure that matched no watcher pattern

The codex CLI went quota-dead and terminated with exit 137 (SIGKILL / OOM-shaped). Octopus's
quota-watcher patterns matched none of that, so codex read as a silent zombie for an extended
period. `_run_codex` has been deleted from `divergence.py`. The OpenAI **API-key** path replaced it
as the second-opinion seat, because `GET /v1/models` gives status-aware health in one cheap call:
401/403 = key dead, 429 = quota (key still valid), 5xx = transient (key NOT disproven), 000 = network.

**Live trap that survives the deletion:** `ace/cli.py`'s escalation hint still prints
`--providers ollama,codex`, and `_PROVIDER_ROWS` still has a `codex` entry, so the banner will
cheerfully render a `🔴 codex` row. `diverge()` filters unknown names out silently. Worse, a list
containing *only* unknown names produces an unhandled crash:

```
$ python3.11 -c "from ace.agents.divergence import diverge; diverge('t', ['codex'])"
ValueError: max_workers must be greater than 0
```
(confirmed T1, 2026-07-29)

Use only `agy` and `ollama`.

---

## 5. Frame monoculture suppression — why the warning sometimes does not fire

`frame_monoculture_risk(branches, live_provider_count)` returns `False` when fewer than 2 providers
contributed, **in multi-provider mode only**. Rationale: with one live seat you cannot distinguish
that seat's framing bias from genuine structural monoculture, so the warning would be noise. In
frames-only mode the count gate is skipped (`monoculture_provider_count = None`) because diversity
there is frame-based rather than provider-based.

Consequence in practice: on a default `--providers agy` run there is exactly one live provider, so
**you will normally never see the monoculture warning**. Do not read its absence as diversity.

---

## 6. Calibrating expectations for the escalation alarm

`AGREEMENT_ESCALATION = 0.80` is applied to `inter_frame_agreement`, the mean pairwise Jaccard
similarity of stopword-filtered, lowercase, alpha-only tokens of length ≥ 4 (`_extract_keywords`).

Measured on this branch (T1, 2026-07-29):

| Branch set | agreement | escalate |
|---|---|---|
| Three heavy paraphrases of one idea | `0.387` | `False` |
| Three near-verbatim restatements | `1.000` | `True` |

Read: the alarm catches **vocabulary collapse**, not conceptual redundancy. Three branches saying
the same thing in different words will not trip it. That is precisely why the doctrine requires an
unconditional cross-family probe on high-stakes items instead of waiting for the alarm.

---

## 7. Where the `ace` on your PATH actually comes from

`/usr/local/bin/ace` is an editable install that resolves the package to
`/Users/sebastianziegler/ace/ace/__init__.py` — the **owner's working tree**, not the
`~/ace` checkout (merged from the ace-unify worktree). Verified 2026-07-29:

```
$ /usr/local/bin/python3.11 -c "import ace; print(ace.__file__)"
/Users/sebastianziegler/ace/ace/__init__.py
```

So `ace run …` may execute *different code* from the branch you are reading. To exercise this
branch specifically:

```bash tier=T3 verified=2026-07-29
cd /Users/sebastianziegler/ace && /usr/local/bin/python3.11 -m ace.cli run "<topic>" ...
```

Note also that system `python3` is 3.9 and cannot even import this package (modern type syntax).
Always use `/usr/local/bin/python3.11`.

Concretely, the PATH build is missing everything the skill documents. Verified 2026-07-29:

| Command against `/usr/local/bin/ace` | Result |
|---|---|
| `ace banner --preset architecture --providers agy` | `Error: No such command 'banner'.` |
| `ace run "x" --mode a --preset architecture` | `Error: No such option '--mode'. Did you mean '--human-mode'?` |
| `ace run "x" --coherence-floor 0.7 …` | `Error: No such option '--coherence-floor'.` |
| `ace run --help` | `--providers` default is `codex,agy`; preset list has no human presets |
| `ls ~/ace/ace/coupling/` | `__init__.py function.py` — **no `routing.py`**, so no `⇄ ROUTING` line |
| `grep 'def _run_' ~/ace/ace/agents/divergence.py` | `_run_codex`, `_run_gemini`, `_run_agy` |

---

## 8. Verified seat sentinels

Pasted output, T1, executed 2026-07-29.

```
$ ~/.claude/scripts/adapters/ollama.sh --health
OLLAMA-OK (qwen2.5-coder:7b)

$ ~/.claude/scripts/adapters/doctor.sh --fast
ACE provider health — 2026-07-29 21:21
─────────────────────────────────────────────
ollama   ✅ OLLAMA-OK (qwen2.5-coder:7b)
openai   ✅ OPENAI-OK (key valid; 119 models available)
agy      ⏭  skipped (--fast)
handoff  ✅ handoff-v2.sh present + parses
─────────────────────────────────────────────
ALL SEATS HEALTHY
```

```
$ ~/.claude/scripts/adapters/agy.sh --health      # T3 — verified: manual 2026-07-29
AGY-OK (mode=argv)                                 # ~8s
```

The full-fleet run (no `--fast`) additionally exercises agy and is therefore **T3**.

---

## 9. The interactive `Focus` prompt kills non-interactive runs

`ace run` ends every cycle with `click.prompt("Focus", default="4")`. Under the Bash tool — or any
shell without a tty — click cannot read and raises:

```
$ /usr/local/bin/python3.11 -c "import click; click.prompt('Focus', default='4')" < /dev/null
  File ".../click/termui.py", line 201, in prompt_func
    raise Abort() from None
click.exceptions.Abort
```
(confirmed T1, 2026-07-29)

The abort happens **after** divergence has already dispatched, so the quota is spent and the cycle
is lost. Always feed the answer on stdin, one line per cycle:

```bash tier=T3 verified=2026-07-29
printf '2\n' | /usr/local/bin/python3.11 -m ace.cli run "<topic>" --preset architecture --cycles 1
printf '2\n4\n' | /usr/local/bin/python3.11 -m ace.cli run "<topic>" --preset architecture --cycles 2
```

`--preset` also suppresses the two *opening* prompts (root mode + preset selection), because
`cli.py` sets `mode = preset_obj.mode` when `--preset` is given and `--mode` is not. Omitting
`--preset` adds two more stdin lines you must supply.
