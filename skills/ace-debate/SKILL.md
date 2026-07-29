---
name: ace-debate
description: >-
  Run a structured cognitive-divergence debate on a decision using the ACE engine —
  cognitive frames on a strong model, plus an optional different-model-family seat.
  Use when the user says "debate this", "/ACE:debate", "run a debate on X", "get a
  second opinion from another model", "give me multiple perspectives on this",
  "challenge / poke holes in a specific decision or design I've already described
  (one shot)", "red-team this design", "attack / critique an existing plan, RFC,
  design doc or threat model", "am I missing a blind spot?", "diverge on this before
  we decide", or "is this the right approach?".
  Debate generates the opposing branches FOR you in a single pass. If the user wants an
  interactive multi-cycle session where THEY supply the ideas and ACE reflects them
  back, that is the `ace` skill in Mirror mode, not this one.
  Debate owns critique of an artifact that already exists; ACE:plan's internal review
  pass never handles a user-supplied plan. For turning an already-made decision into an
  ordered executable plan, use ACE:plan instead.
  If the failure is that a seat produced nothing at all, use ACE:doctor first — do not
  read the debate troubleshooting reference for a dead seat.
  Successor to the retired /octo:debate, /octo:skill-debate and /octo:council; if those
  are still installed they will also match "debate this" — prefer ACE:debate, because
  the Octopus versions dispatch to providers that no longer exist (codex is quota-dead,
  the gemini CLI is retired).
---

# /ACE:debate — cognitive-divergence debate

Debate is ACE's **divergence** command. It deliberately generates disagreeing views of one
problem, scores them, and hands you a synthesis prompt. It does **not** hand you an answer —
you (or Claude, as the synthesis engine) close the loop.

Evidence for its existence: `/octo:debate` was invoked 12 times by the owner — the highest-demand
survivor of the Octopus retirement, and the most recent Octopus command run before the migration.

**Vocabulary (defined once):**

| Term | Meaning |
|---|---|
| **Branch** | One candidate idea/angle parsed out of a provider's numbered list. |
| **Frame** | A goal-function redirect prepended to the prompt ("you are a regulator…"). 15 exist. |
| **Provider / seat** | An external CLI that generates branches. Post-prune: `agy` and `ollama` only. |
| **Frames-only** | *Intended:* divergence by frames on a single model, no external dispatch. **On this branch it does not do this** — see the defect box under *Quick start*. |
| **Root mode** | `ai`/`a` = GOVERNOR (scaffolds the AI's thinking; the debate default). `h`/`human` = MIRROR (scaffolds yours). Set automatically from `--preset`. |
| **Coupling function** | The scorer/bookkeeper that decides which branches integrate vs defer. |
| **Zombie seat** | A provider that looks healthy but returns empty or off-topic output. |
| **Routing line** | The `⇄ ROUTING` output line: which synthesis model to use, and whether to escalate. |

---

## When to use this — and when not to

| Situation | Command |
|---|---|
| Decision is open; you want the option space widened and stress-tested | **/ACE:debate** |
| You want to know if you are wrong / what you are not seeing | **/ACE:debate** |
| Threat modelling, adversarial review, "how would this be abused" | **/ACE:debate** (`--preset frames-adversarial`) |
| Decision is made; you want an ordered, falsifiable execution plan | **/ACE:plan** |
| You want to know whether the seats are alive before spending quota | **/ACE:doctor** |
| You just want one good answer fast | Neither — ask Claude directly |

**Do not use debate to make the decision for you.** Its output is a branch set plus a synthesis
prompt. If you want convergence, that is `/ACE:plan`'s job by design (§ *No weak peer in planning*).

---

## Quick start

Debate is a **protocol on top of `ace run`** — there is no `ace debate` subcommand. The three
real entry points are `ace run`, `ace banner`, `ace debt`.

> **⚠ The `ace` on your PATH is not this branch.** `/usr/local/bin/ace` is an editable install
> resolving the package to `/Users/sebastianziegler/ace/ace/__init__.py` — the owner's working
> tree (verified T1, 2026-07-29). That build has **no `banner` subcommand, no `--mode`, no
> `--coherence-floor`, and no `ace/coupling/routing.py` (so no `⇄ ROUTING` line)**, and its
> `--providers` still defaults to `codex,agy`. Everything documented here was read off
> `feat/ace-unified`. Exercise **this** branch explicitly:
> `cd /Users/sebastianziegler/ace-unify && /usr/local/bin/python3.11 -m ace.cli <subcommand> …`
> System `python3` is 3.9 and cannot import the package. Details:
> [references/troubleshooting.md §7](references/troubleshooting.md).

Every fence below assumes you are already in `/Users/sebastianziegler/ace-unify`.

```bash tier=T3 verified=2026-07-29
# T1 — preflight: what will this cost me, and are the seats alive?
cd /Users/sebastianziegler/ace-unify
/usr/local/bin/python3.11 -m ace.cli banner --preset architecture --providers agy
~/.claude/scripts/adapters/doctor.sh --fast
```

```bash tier=T3 verified=2026-07-29
# T3 — the real thing (dispatches the agy seat; consumes OAuth quota).
# Pipe the Focus answer — see the interactivity note below.
printf '2\n' | /usr/local/bin/python3.11 -m ace.cli run \
  "SQLite R-tree vs Postgres PostGIS for the 360 frame index" \
  --preset architecture --cycles 1 --providers agy
```

```bash tier=T3 verified=2026-07-29
# T3 — frames-only preset. ⚠ Still dispatches to --providers (default agy). See the box below.
printf '4\n' | /usr/local/bin/python3.11 -m ace.cli run "<topic>" --preset frames-deep --cycles 1

# T1 — PRIVACY-BOUND ONLY: local seat, nothing leaves the box. NOT a debate peer —
# branches are 7B-quality and get discounted on read. Note the non-frames_only preset,
# which is what keeps frame injection switched on for the local seat.
printf '2\n' | /usr/local/bin/python3.11 -m ace.cli run "<topic>" \
  --preset architecture --cycles 1 --providers ollama
```

> **⚠ Engine defect, verified on this branch 2026-07-29.** `frames-deep` /
> `frames-adversarial` print *"Frames-only mode … No multi-provider dispatch"*, but
> `run()` still calls `diverge(topic, provider_list, use_frames=not profile.frames_only)`
> with `provider_list` defaulting to `agy`. The only thing `frames_only` actually changes
> is that **frame injection is switched off** — the external seat is still dispatched, and
> `FRAMES_DEEP_SET` / `FRAMES_ADVERSARIAL_SET` are defined but never read by any code path
> (`grep -rn FRAMES_DEEP_SET ace/` matches only the definition line).
> Do **not** reach for `--preset frames-deep` as the no-cloud workaround: `frames_only=True`
> makes `diverge()` run with `use_frames=False`, so `frame_assignments = {p: None}` and you
> get an *unframed* single seat — no frames **and** no cross-family — while
> `max_frame_dominance` silently degrades to its keyword-prevalence fallback
> (`routing.py:75–89`). Use any non-`frames_only` preset with `--providers ollama` instead.

**`ace run` prompts for a synthesis focus at the end of *each* cycle.** Piping the answer is
mandatory when a model runs it: with no tty the prompt raises `click.exceptions.Abort` and the
cycle is lost **after the seat has already been paid for**. One line of stdin per cycle.
(Verified T1, 2026-07-29.)

**The Focus menu (GOVERNOR / ai mode)** — `[4]` is the default:

| # | Focus | Asks |
|---|---|---|
| 1 | Trajectory update | Where does the trajectory now point? What shifted? |
| 2 | Load-bearing vs noise | Which branches are load-bearing, which are tangents? |
| 3 | Next step | What is the next concrete, falsifiable step? |
| 4 | Full Governor | All three (default) |

MIRROR mode (`--mode h`) shows a different four — Tensions / Hidden question / Uncomfortable
branch / Full Mirror — so these numbers do not carry over. (Source: `ace/cli.py:383–441`, T1.)

`--preset` alone is enough to skip **both** opening questions: `cli.py` reads the root mode off
the preset (`mode = preset_obj.mode`; ai presets are `ai` = GOVERNOR). Pass `--mode h` only if
you want the MIRROR variant, where the *human* is the divergence engine — it also swaps the
Focus menu above.

---

## How the engine actually works

Read the source before you trust any description: `ace/agents/divergence.py`.

```
ace run TOPIC
  └─ diverge(topic, provider_list, use_frames = not profile.frames_only)
       ├─ _select_frame(provider, used_frames)      # FRAME_PROVIDER_AFFINITY, no two seats share a frame
       ├─ ThreadPoolExecutor                        # all seats run in PARALLEL
       │    ├─ _run_agy(topic, frame)    → agy.sh   → _parse_branches
       │    └─ _run_ollama(topic, frame) → ollama.sh→ _parse_branches
       │         (each builds its prompt via _build_framed_prompt)
       └─ _score_branches(all_branches, topic)      # novelty / coherence / frame_saturation
  ├─ coupling.apply_coherence_floor(...)            # only if profile.coherence_floor > 0
  ├─ coupling.frame_monoculture_risk(...)           # >80% one frame
  ├─ recommend_routing(all_branches)                # ace/coupling/routing.py → the ⇄ ROUTING line
  ├─ coupling.integrate(b) for each branch          # attractor-debt bookkeeping
  └─ synthesis menu → paste-into-Claude panel
```

Key facts that are easy to get wrong:

- **Scoring is heuristic, not an LLM call.** `_score_branches` computes novelty from inter-branch
  word overlap, coherence from topic-word overlap × length, frame_saturation from overlap with the
  frame prompt. `low_trust_flag = coherence < 0.3`. No extra tokens are spent.
- **Scores WEIGHT, they do not PRUNE** — unless you explicitly set a coherence floor
  (`--coherence-floor`, or the MIRROR preset `human-scientific`, which sets 0.70). Default is 0.0 = off.
- **`_parse_branches` only accepts lines starting with a digit, `-`, `*`, or `•`, with >10 chars of
  content.** A seat that answers in prose paragraphs yields **zero branches** while reporting
  `available=True`. This is the most common silent failure.
- **Only two runners exist.** `runners = {"agy": _run_agy, "ollama": _run_ollama}`. `_run_codex` and
  `_run_gemini` were deleted (codex quota-dead, exit 137; gemini CLI retired).

### The fleet, post-prune (2026-07)

| Seat | Family | Role in debate | Frames it draws (affinity) |
|---|---|---|---|
| `agy` | Google / Gemini via Antigravity | **Research-breadth + decorrelated voice.** The only genuine cross-family seat. | biology, markets, ten-year-old, regulator, hardware-engineer, ops-3am, extreme-zero, speedrunner |
| `ollama` | local Qwen | **Not a debate peer** (see below). Privacy-bound and bulk work. | game-design, logistics, ant-colony, adversary, inversion, extreme-infinite, remove-assumption |
| Claude | — | Synthesis engine. Reads the panel, holds the trajectory. | — |

`agy`'s grounding was independently verified: asked to fetch
`api.github.com/repos/ollama/ollama/releases/latest` it returned `v0.32.5`, matching Claude's own
fetch exactly. It genuinely retrieves live sources rather than reciting training data.
(verified: manual 2026-07-29)

Full 15-frame catalog with "when each frame bites": **[references/frame-catalog.md](references/frame-catalog.md)**

---

## Choosing a divergence strategy

**Frames are the default.** Cross-family orthogonality among frontier models is modest
(~15–25pp uncorrelated) because they share a training corpus. Swapping families buys less than
people assume, at clustered-fragility cost.

| Condition | Strategy | Flags |
|---|---|---|
| Default / conceptual / evaluative work | Frames on one seat | `--preset architecture --providers agy` |
| Threat modelling, security, needs reproducibility | Adversarial posture | `--preset frames-adversarial` |
| **Data must not leave the box** (PII / GDPR) | Local seat only, branches discounted | `--providers ollama` |
| Quota exhausted, topic is **not** privacy-bound | Do **not** substitute `ollama`. Run frames on Claude in-conversation, or defer until quota resets | — |
| Shared-blind-spot alarm fired (`inter_frame_agreement > 0.80`) | Add a family you are **not already using** | `--providers agy` if you ran frames-only; otherwise a manual `openai.sh` probe (T3) |
| **High-stakes item** (irreversible, expensive, or safety-relevant) | Add a different family **unconditionally** | same as above — `agy` if unused, else the manual `openai.sh` probe (T3) |

That last row is the important one. Frames decorrelate the **question-space explored**, not the
**error distribution** — every frame still runs on one model and inherits its factual priors. On
high-stakes items fire one cross-family probe regardless of what the agreement signal says.

Reinforcing that: the `> 0.80` alarm is **conservative in practice**. Measured on this branch
(T1, executed 2026-07-29) three heavily-paraphrased branches expressing the *same* idea scored
`inter_frame_agreement = 0.387` — well below the trigger. Only near-verbatim vocabulary reuse
reached `1.0`. Treat a silent alarm as weak evidence, not as an all-clear.

---

## Reading the routing line

Every cycle prints one:

```
⇄ ROUTING — regime: converging | recommend Sonnet/Haiku-class (convergent) synthesis
  survival=1.00 dominance=1.00 agreement=0.39
```

| Signal | Source | Meaning |
|---|---|---|
| `survival` | `branch_survival_rate` | Fraction of branches not low-trust and coherence ≥ 0.30. |
| `dominance` | `max_frame_dominance` | Share held by the single most common frame. |
| `agreement` | `inter_frame_agreement` | Mean pairwise keyword Jaccard across branches. |

Thresholds live in `ace/coupling/routing.py`: `SURVIVAL_UNDERDETERMINED = 0.40`,
`FRAME_DOMINANCE_CEILING = 0.60`, `SURVIVAL_AMBIGUOUS = 0.50`, `AGREEMENT_ESCALATION = 0.80`.

- `regime: underdetermined` or `ambiguous` → routes to **Opus**. No trajectory has formed, so
  synthesis is secretly a second divergence and needs a model that holds implausible combinations
  alive. The safe-failure bias is deliberate: mis-routing an open question to a convergent model
  launders it as a confident premature answer.
- `regime: converging` → **Sonnet/Haiku-class** is correct and cheaper.
- `↑ ESCALATE DIVERGENCE` → the shared-blind-spot alarm. Add a different family next cycle.

---

## The asymmetric aggregation rule

This is the doctrine that keeps debate from degrading into a vote. **Memorise it.**

1. An external seat's **disagreement** is a flag: re-examine that point with the strong model.
2. An external seat's **agreement** counts for **nothing**. It is not corroboration — a weaker or
   differently-aligned model may agree from incapacity, and the coupling function cannot tell
   incapacity apart from judgment.
3. **No external seat ever gets a vote that overturns Claude.** There is no majority rule here.

Corollary: never report "2 of 3 seats agreed" as a result. Report *what was disagreed about*.

### Why there is no local model as a debate peer

Frames-on-a-frontier-model beats Claude-vs-7B on every axis: branch quality, on-topic rate, and
signal value of disagreement. A local 7B disagreeing tells you the 7B is weak, not that the idea is
wrong — pure noise injected into the aggregation.

`ollama` exists in the runner table for **privacy-bound work** (data that must not leave the box —
note `gpt-oss:120b-cloud` is *cloud* despite living in ollama, so never route PII there) and
**bulk/overnight** work. Use it as a debate seat only when the topic cannot be sent off-box at all,
and then discount its branches accordingly.

---

## The zombie gate

A seat that passes `command -v` but returns empty or off-topic output provides **zero value while
reporting healthy**, and its vacuous "agreement" gets miscounted as concurrence. Real on-disk
exhibit: a debate round file byte-identical to a `.err` file containing a Gemini `IneligibleTierError`
stack trace, filed as a legitimate debate round. Non-empty checks, `size > 500B` checks, and
file-exists checks **all pass on that file**.

Both runners now close the gate. In `_run_agy` / `_run_ollama`:

```python
if result.returncode != 0 or not raw:
    return DivergenceResult(..., available=False, error=(result.stderr.strip() or "empty_output")[:200])
```

plus `_is_quota_error(raw)` → `available=False, error="quota_exceeded"` for agy.

**How to read a run:**

| What you see | Verdict |
|---|---|
| `🧭 agy [regulator] (14.2s) — 6 branches:` + distinct one-liners | Real branch set. |
| `🧭 agy: unavailable (quota_exceeded)` | Honest failure. The gate worked. Nothing was counted. |
| `🧭 agy: unavailable (empty_output)` | Honest failure. Seat produced nothing. |
| Seat listed as available with **0 branches** and no error | **Zombie-adjacent** — the seat replied in prose and `_parse_branches` found no list. Re-run; if it repeats, treat the seat as dead for this topic. |
| `No branches from any divergence provider` then exit 1 | Every seat failed. Run `/ACE:doctor`. |

`available=False` means: **excluded from `live_providers`, contributes zero branches, and suppresses
the frame-monoculture warning** (which is gated on `< 2` live providers in multi-provider mode,
because one seat's framing bias is indistinguishable from structural monoculture).

Verified seat sentinels with their real pasted output:
**[references/troubleshooting.md §8](references/troubleshooting.md)** (T1, executed 2026-07-29).

---

## Worked example — the shape of a run

Topic: *SQLite R-tree vs Postgres PostGIS for the 360 frame index.* Reversible, moderate stakes,
one live cross-family seat.

1. **Preflight (T1)** — `doctor.sh --fast`, then `banner --preset architecture --providers agy`.
   A banner row is a PATH lookup; `doctor.sh` is what actually exercises the seat.
2. **Cheap first pass, free** — run three or four frames yourself, in this conversation.
   **Not** `--providers ollama`: this topic is not privacy-bound, so a 7B buys nothing.
3. **One cross-family probe (T3)** — `printf '2\n' | … run "<topic>" --preset architecture
   --cycles 1 --providers agy`. The `printf` is mandatory, not decoration.
4. **Read the routing line** — `underdetermined` → another cycle before you trust the panel.
   `↑ ESCALATE DIVERGENCE` with agy already spent → manual `openai.sh` probe (T3).
5. **Aggregate asymmetrically** — carry only agy's *disagreements* into Claude. Its agreement is
   not evidence and must never be written up as concurrence.
6. **Synthesize, then hand off** to `/ACE:plan` if the decision is now made.

Full narrative with real pasted output at every step:
**[references/worked-example.md](references/worked-example.md)**

---

## Triage

| Symptom | Cause | Action |
|---|---|---|
| `agy: unavailable (quota_exceeded)` | OAuth quota group exhausted | Run frames on Claude in-conversation, or fire a manual `openai.sh` probe (T3); retry agy tomorrow. Do **not** substitute `ollama` unless the topic is privacy-bound. Never pass `--model` to agy — that caused the original quota-group incident. |
| Banner said "no external providers used" but agy was still called | The frames-only defect (see box above) | Name the seat you actually want with `--providers`; do not trust the preset's claim. |
| `agy: unavailable (empty_output)` | Auth expired, or an agy version bump changed the input contract | `~/.claude/scripts/adapters/agy.sh --health` (T3). Re-auth via agy's own login. Re-run `--health` after every agy version bump. |
| Seat available, **0 branches** | Reply was prose; `_parse_branches` needs `1.`/`-`/`*`/`•` lines | Re-run. If it repeats, the seat is effectively dead for this topic — drop it and run the frames on Claude in-conversation. |
| `ollama: unavailable`, message mentions FAIL CLOSED | Model not present locally; the adapter refuses to auto-pull (a cascade once triggered a ~42 GB download) | Pre-pull explicitly: `ollama pull qwen2.5-coder:7b`. |
| `No branches from any divergence provider` → exit 1 | Every seat failed | `/ACE:doctor`. Then run the frames on Claude in-conversation rather than re-dispatching. |
| `ValueError: max_workers must be greater than 0` | Every name in `--providers` is unknown to the runner table (e.g. `--providers codex`) | Use only `agy` and/or `ollama`. Unknown names are silently dropped by `diverge()`; an all-unknown list crashes. (Confirmed T1, 2026-07-29.) |
| Every branch reads like one idea rephrased | Frame monoculture | Look for the `⚠ FRAME MONOCULTURE` line. Switch to `--preset frames-adversarial` for one cycle. |
| Branches are metaphor-heavy and unactionable | Coherence floor is off (default 0.0) | Add `--coherence-floor 0.70`. |
| Synthesis panel feels like noise | Too many branches | Lower `--cycles`, or pick focus `[2]`/`[3]` instead of `[4]`. |

Longer incident chronicles: **[references/troubleshooting.md](references/troubleshooting.md)**

---

## Limitations — state these, do not hide them

1. **No rebuttal round.** Today's flow is one-shot diverge → synthesize. Branches never see each
   other; nothing is rebutted. Calling it a "debate" is a slight overclaim. This is a known
   enhancement, not a launch blocker.
2. **Frames decorrelate the question-space, not the error distribution.** Fifteen frames on one
   model share that model's factual priors.
3. **Scoring is keyword heuristics.** Novelty/coherence are word-overlap proxies, not judgments.
4. **The escalation alarm is conservative** — measured 0.387 on genuinely-redundant paraphrases
   (T1, 2026-07-29). Do not rely on its silence.
5. **Only one cross-family seat is wired into the engine.** `diverge()` has exactly two runners
   (`agy`, `ollama`); `openai` is not among them (`grep -rn openai ace/` → no matches, 2026-07-29).
   The OpenAI API-key seat *is* the designated primary second-opinion path (see `/ACE:doctor`),
   but on this branch it must be fired manually, out of band:
   `~/.claude/scripts/adapters/openai.sh "<prompt>"` (T3). With `agy` down the engine has no
   second family — you have to run that probe yourself and fold it in by hand.
6. **`frames_only` does not do what its name says** on this branch — it disables frame injection
   but does not stop external dispatch, and the two frame sets it advertises are dead code.
   Open defect; see the box under *Quick start*.
7. **The banner lies about the fleet.** `_PROVIDER_ROWS` in `ace/cli.py` still carries entries for
   `codex` and `gemini` (both runners deleted) and has **no** entry for `ollama`, which therefore
   renders with the generic `🟡 … — divergence` fallback. A banner row is a PATH lookup
   (`shutil.which`), not proof the seat can produce branches — use `/ACE:doctor` for that.

---

## Provenance and maintenance

Facts here are dated **2026-07-29** and read off branch `feat/ace-unified` — **not** off the `ace`
on your PATH (see the caveat under *Quick start*). Run every check below from
`/Users/sebastianziegler/ace-unify`:

| Claim | Re-verification (tier) |
|---|---|
| Runner table is exactly `agy` + `ollama` | `grep -n 'runners: dict' -A2 ace/agents/divergence.py` (T1) |
| Frame affinity lists | `grep -n 'FRAME_PROVIDER_AFFINITY' -A10 ace/agents/divergence.py` (T1) |
| Real `ace run` flags | `/usr/local/bin/python3.11 -m ace.cli run --help` (T1) |
| Preset list | `/usr/local/bin/python3.11 -m ace.cli banner --help` (T1) |
| PATH `ace` is the *other* tree | `cd ~ && /usr/local/bin/python3.11 -c "import ace; print(ace.__file__)"` (T1) |
| Focus menu wording | `sed -n '383,441p' ace/cli.py` (T1) |
| Routing thresholds | `grep -n '^[A-Z_]* =' ace/coupling/routing.py` (T1) |
| Seat health | `~/.claude/scripts/adapters/doctor.sh` (T1 for `--fast`; full run touches agy = T3) |
| Suite green | `/usr/local/bin/python3.11 -m pytest -q` → `35 passed` (T1, 2026-07-29) |
| agy invocation contract | `~/.claude/scripts/adapters/HARVEST.md` (T1 read) |

**Re-run `agy.sh --health` after every agy version bump** — the input contract has changed across
versions before, and the failure mode is a silent zombie.
