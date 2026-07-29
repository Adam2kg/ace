---
name: ace-plan
description: >-
  Turn a decision that is already made into an ordered, falsifiable execution plan —
  each step carrying the observation that would prove it wrong and the gate that must
  pass before the next step starts. Use when the user says "plan this", "give me an
  implementation plan", "what are the steps to ship X", "break this into phases",
  "sequence the migration", "build a rollout plan with checkpoints", "ACE plan this", or
  "what's the next falsifiable step". Runs on a SINGLE strong model (GOVERNOR mode) by
  design; the only external involvement is one optional decorrelated review pass that runs
  INSIDE this command, over the plan this command just authored. That pass is not an entry
  point: if the user arrives WITH an existing plan, RFC, or design doc and wants it
  attacked, critiqued, or red-teamed, that is /ACE:debate, not this skill. Do NOT use when
  the decision itself is still open or you want options generated — that is /ACE:debate.
  Successor to the retired "/octo:plan"; if the user literally types /octo:plan and the
  legacy Octopus plugin is still installed, that command answers first — say so and offer
  /ACE:plan rather than silently claiming the invocation.
---

# /ACE:plan — converge on a falsifiable execution plan

**Successor to `/octo:plan`** (9 real invocations in the Claude-Octopus history — the only
planning surface with demonstrated demand). Retirement is *planned, not done*: if the legacy
Octopus plugin is still installed on this machine, a literal `/octo:plan` still resolves to
Octopus and answers first. Say so and offer `/ACE:plan` rather than silently claiming the
invocation.

`/ACE:plan` is the **convergent** half of the ACE pair: `/ACE:debate` widens the search space,
`/ACE:plan` collapses it. Everything below follows from that one asymmetry.

**Contract:** you bring a decision that is already made; the command returns an ordered
sequence of steps, each stating what would falsify it and what observation gates the next one.

---

## When to use this — and when not to

| You have… | Use | Why |
|---|---|---|
| A chosen direction, need the sequence | **/ACE:plan** | Planning is synthesis: one strong model, minimize entropy |
| Two or more live options, no decision | **/ACE:debate** | You need divergence, not convergence |
| A plan that already exists, want it attacked | **/ACE:debate** (`--preset frames-adversarial`) — always | Critique is divergence over an artifact. This command's review pass only ever runs on a plan it just authored in this session. |
| "Is my provider fleet alive?" | **/ACE:doctor** | Health only |
| A vague feeling that something is wrong | **/ACE:debate** | Nothing to sequence yet |

**The retrieval collision to get right:** both commands fire on the word *plan*. The
discriminator is **whether the decision is settled**, not whether the word appears.

- *"Should we migrate to Postgres or stay on SQLite?"* → **debate**. No decision.
- *"We're migrating to Postgres — plan it."* → **plan**. Decision made, sequence unknown.
- *"Plan the migration and tell me if it's the right call."* → **debate first, then plan**, in
  that order, said out loud. Do not silently merge the two.

If you are inside `/ACE:plan` and discover the decision is *not* settled, **stop and say so**.
A confident sequence over an unsettled decision is the exact failure this command exists to
avoid.

---

## Why there is no second voice here

Planning *is* the synthesis role. ACE's own preset engine records why a weak partner cannot
help with synthesis — from the module docstring of `ace/presets.py`:

> A weaker synthesis agent defers from INCAPACITY, not judgment — the coupling function
> cannot distinguish these, so convergence warnings fire for the wrong reason.

(The **coupling function** — `ace/coupling/function.py` — is the scorer that decides how
strongly ACE pushes toward or away from convergence; it reads agreement between branches and
has no signal for whether a branch was *capable* of disagreeing.)

As an operational rule: a weak peer that agrees with your plan has told you **nothing** — it
may have agreed because the plan is sound, or because it could not model the problem well
enough to object. The coupling function measures agreement, not competence, and scores those
two cases identically. So a weak peer does not add signal; it manufactures false confidence,
which is worse than no second opinion at all.

This is the opposite shape from `/ACE:debate`, where many cheap framed voices are exactly right
because there the goal is coverage of the question space, not correctness of a verdict.

**Corollary:** never put local Qwen (`ollama.sh`) in a planning-review seat. Local models are
for privacy-bound and bulk work, never independent judgment.

---

## GOVERNOR mode — what the code actually does

ACE declares a **root mode** at the top of every session (`ace/cli.py`, the `--mode` option):

| | MIRROR (`--mode h` / `human`) | GOVERNOR (`--mode a` / `ai`) |
|---|---|---|
| Who is thinking | The human | The AI |
| Coupling target | **Maximize** entropy — unstick attractors, scaffold reflection | **Minimize** entropy — converge toward resolution |
| Synthesis menu | Tensions / Hidden question / Uncomfortable branch / Full Mirror | Trajectory update / Load-bearing vs noise / **Next step** / Full Governor |
| Convergence warning | Fires on sustained high agreement (≥0.75, after ≥2 trajectory segments) — premature closure risk | Fires on high agreement (≥0.80) with unspent interrupt budget — creative-capture risk |

Suppression is *not* a mode property — the warning fires in **both** modes
(`CouplingFunction.convergence_warning`, `ace/coupling/function.py:581`). What suppresses it is
the per-preset `convergence_warning_enabled` field plus the `--human-mode` flag
(`apply_human_mode`, `ace/presets.py:304`), and those cut across mode in both directions
(`human-scientific` is MIRROR and sets it `True`; `frames-adversarial` is GOVERNOR and sets it
`False`). Note that field is currently **not consulted at the warning site** —
`ace/agents/synthesis.py:149` calls `coupling.convergence_warning()` unconditionally — so the
warning fires regardless. Verified 2026-07-29.

`/ACE:plan` is **GOVERNOR, always**. Verified preset → mode mapping (read live from
`ace/presets.py`, 2026-07-29):

| mode | presets |
|---|---|
| `ai` (GOVERNOR) | `architecture`, `debugging`, `design-review`, `looping`, `frames-deep`, `frames-adversarial` |
| `human` (MIRROR) | `human-adhd`, `human-scientific`, `human-creative` |

The falsifiability requirement is not a stylistic preference invented here — it is the literal
Governor synthesis instruction in `ace/cli.py`:

> "What is the next concrete, testable step this trajectory points toward? State it as a
> falsifiable claim."

`/ACE:plan` applies that instruction to **every** step, not just the last one.

**Do you need the `ace` CLI to run this command?** No. The engine is a *divergence* engine;
planning is synthesis, and this Claude conversation is the synthesis engine. The CLI is
optional scaffolding — see `references/cli-scaffolding.md` for when it earns its keep.

---

## The falsifiable-step template

Every step in the output uses this shape. A step missing **Falsifier** or **Gate** is not a
step, it is a wish.

```markdown
### Step N — <imperative action, one line>
- **Deliverable:** <the artifact that exists when this step is done>
- **Falsifier:** <the concrete observation that would prove this step wrong or unnecessary>
- **Gate:** <the check that must pass before Step N+1 starts — a command, a metric, a review>
- **Rollback:** <how to undo this step, or "n/a — additive only">
- **Cost:** <S / M / L, and what dominates it>
```

Rules for filling it in:

- **Falsifier must be observable before the step is finished**, not after the project ships.
  "Users don't like it" is not a falsifier; "p95 stays above 400 ms on the staging replay" is.
- **Gate must be checkable by someone who was not in this conversation.** Prefer a command over
  a judgement call.
- **A step whose falsifier you cannot name is a research task, not an execution step.** Split
  it: make Step N "answer question Q", with the answer itself as the gate.
- **Order by information gain, not dependency alone** — cheap disconfirmation goes early.
- **Cap the plan at the first hard gate.** Say "re-plan after Gate 3" instead of inventing
  Steps 4–9 whose premises that gate could erase.

---

## Procedure

**Step 1 — Confirm the decision is settled.** Restate the decision in one sentence and the
alternatives that were rejected. If you cannot name a rejected alternative, the decision
probably is not made — route to `/ACE:debate`.

**Step 2 — Name the load-bearing insight.** One sentence: the thing that, if false, makes the
whole plan wrong. This becomes the falsifier of Step 1 or 2.

**Step 3 — Draft steps using the template above.** 3–7 steps for most work. More than ~9 means
you are planning past a gate.

**Step 4 — Self-check against the failure list:**

- [ ] Every step has a Falsifier and a Gate
- [ ] At least one step could kill the plan, and it is early
- [ ] No step depends on an unnamed assumption
- [ ] The plan stops at the first hard gate
- [ ] Rollback is stated wherever the step is destructive

**Step 5 — Write the plan to a file** so the optional review pass can read it (and so the plan
outlives the conversation). `PLAN.md` in the project root is the default.

**Step 6 (optional) — one decorrelated review pass.** See below. Skip it for low-stakes or
easily-reversible plans; it costs quota and a few minutes.

---

## The optional decorrelated pass

This is the **only** external involvement in `/ACE:plan`, and it happens **after** the plan is
finished — never during drafting. A second voice during drafting is a peer; a second voice
over a finished artifact is a reviewer. Only the second one is useful here.

### When it is worth it

Fire it when **any** of these hold:

- The plan is hard to reverse (data migration, public API change, anything touching money).
- The plan rests on a factual claim about the outside world that may have drifted (an API
  still existing, a version being current, a limit being what you remember).
- You are the author *and* the reviewer and have been for several hours.

Skip it when the plan is additive, cheap to undo, and entirely inside code you control.

**What this pass cannot do.** A `/ACE:plan` draft has no frame diversity at all — one model,
one prior set — so every factual assumption in it is Claude's. A different-family pass
decorrelates the *errors* only partly (~15–25pp uncorrelated; the shared training corpus caps
it), and it decorrelates nothing about the question-space you never thought to explore. If you
suspect the whole framing is wrong rather than a step being wrong, this pass will not find it:
go to `/ACE:debate`.

### Which seat

| Risk you are testing | Seat | Why |
|---|---|---|
| **Factual currency** — "is this still true out there?" | `agy.sh` | Research-breadth seat; verified to fetch live sources, not recall (see Provenance) |
| **Reasoning blind spot** — "what failure mode did I miss?" | `openai.sh` | Different training family → **partly** decorrelated errors (~15–25pp uncorrelated; shared corpus caps it). Primary second-opinion seat |
| Anything containing PII or GDPR-bound data | **none of the above** | `openai.sh` is cloud; `gpt-oss:120b-cloud` is cloud *despite living in ollama*. Do the review yourself. |

**One pass per risk, never a tally.** Most plans need exactly one seat. If a plan genuinely
carries both risks — hard to reverse *and* resting on external facts — you may fire one
`openai.sh` reasoning pass and one `agy.sh` currency pass, because they are answering different
questions. What you must never do is compare the two and count concurrence: two seats saying
the same thing is still worth nothing (see *asymmetric aggregation* below). If you catch
yourself writing "both seats flagged X", you are tallying — write "X was flagged" and re-derive
it once.

### How to run it

```bash tier=T3 verified=2026-07-29
# T3 — real paid/OAuth invocation. Do NOT run speculatively.
{ printf '%s\n\n' "$REVIEW_PROMPT"; cat PLAN.md; } \
  | ~/.claude/scripts/adapters/openai.sh || echo 'REVIEW PASS FAILED — no output'
```

The three prompt variants (reasoning / factual-currency / ordering) live in
`references/decorrelated-review.md` — copy one from there; that file is their only home. Swap
`openai.sh` for `agy.sh` when the risk is factual currency. Both adapters accept the prompt on
stdin or as `$1`.

### How to read the result — asymmetric aggregation

This is the rule that makes the pass safe. It is deliberately lopsided:

- **Agreement counts for nothing.** "Looks good" is not evidence. Do not record it, do not let
  it raise your confidence, do not mention it as validation.
- **Disagreement is a flag, not a verdict.** It means *re-examine this with the strong model*.
  You re-derive the point yourself; if it survives your own re-derivation, the plan stands.
- **No external seat ever overturns the plan on its own authority.** There is no vote.
- **An empty or off-topic response is a FAILURE, not a pass — and nothing enforces that for
  you here.** This pass is a raw shell pipe; the zombie gate in `ace/agents/divergence.py`
  (`available=False` on empty output or non-zero exit) protects the *engine* path, not this
  one, and it covers only the two engine runners `_run_agy` and `_run_ollama` — there is no
  openai runner (`divergence.py:339`). `openai.sh` does exit non-zero on empty content
  (`openai.sh:53`), and `ollama.sh` fails closed, but **`agy.sh` does not** — its run path
  (`agy.sh:62–70`) execs the binary and passes agy's own exit code straight through with no
  output check, so an empty agy reply arrives as exit 0 and silence. That is the original
  zombie. So gate it yourself: check `$?`, then apply the on-topic test in
  `references/decorrelated-review.md` ("The zombie gate, applied here" — does the response cite
  at least one step number?). If either check fails, you got no review; say so, do not imply
  you did.

---

## Worked example

Decision already made: *"Cut the ACE plugin's dangling command reference before publishing."*

Below, **Procedure N** refers to the numbered procedure above; the bare word **Step** is
reserved for the plan's own steps.

**Procedure 1 (decision restated).** `plugin.json` points at `./.claude/commands/ace.md`, which
does not exist on this branch. Rejected alternative: ship it and fix in a patch release.

**Procedure 2 (load-bearing insight).** If Claude Code ignores unresolvable entries in
`commands[]`, this is cosmetic and does not gate the release. If it hard-fails plugin load, it
does.

**Procedure 3 (draft steps).**

### Step 1 — Reproduce the failure mode
- **Deliverable:** a recorded observation of what Claude Code does with the dangling path
- **Falsifier:** the plugin loads clean with the dangling entry → this is cosmetic, demote to a chore
- **Gate:** the observation is written down before Step 2 starts
- **Rollback / Cost:** n/a (read-only) / S

### Step 2 — Point `commands[]` at files that exist
- **Deliverable:** `plugin.json` listing only resolvable paths
- **Falsifier:** a listed path still does not resolve from the plugin root
- **Gate:** the path-existence check below prints `True` for every row
- **Rollback / Cost:** `git checkout plugin.json` / S

### Step 3 — Re-run the suite
- **Deliverable:** green test run on the branch
- **Falsifier:** any test regresses
- **Gate:** `pytest -q` reports 0 failures
- **Rollback / Cost:** n/a / S

**Both gates executed live (T1, 2026-07-29):**

```bash tier=T1
set -e   # fail-fast: without this the fence returns only the LAST exit code and a
         # broken step above is silently masked (see the note below)
cd /Users/sebastianziegler/ace-unify
/usr/local/bin/python3.11 -c "import json,os;d=json.load(open('.claude-plugin/plugin.json'));[print(p, os.path.exists(p.lstrip('./'))) for p in d['commands']+d['skills']]"
/usr/local/bin/python3.11 -m pytest -q
```
```
./commands/debate.md True
./commands/plan.md True
./commands/doctor.md True
./skills/ace True
./skills/ace-debate True
./skills/ace-plan True
./skills/ace-doctor True                <-- Step 2 gate PASSES: every manifest path resolves
......................................                                   [100%]
38 passed in 1.06s                      <-- Step 3 gate passes
```

> **Two gate defects this fence caught, both worth internalizing.**
> 1. The manifest was originally at `plugin.json` (repo root). Claude Code requires it at
>    **`.claude-plugin/plugin.json`** — at the root the plugin silently never loads and
>    `/ace:debate` simply does not exist. Moving it changed this command's path.
> 2. Without `set -e`, this fence exited **0** even while the middle command threw
>    `FileNotFoundError`, because only the last command's status is returned. A gate that
>    cannot fail is not a gate — always guard a multi-command fence.

> **Why this gate earns its keep.** When this example was first written, the same command
> printed `./.claude/commands/ace.md False` — `plugin.json` shipped a **dangling command
> path**. The gate caught it; it was fixed in plugin.json v0.2.0 (2026-07-29). A falsifiable
> gate proves its value the day it fails, not the day it passes.

**Procedure 4–5 (self-check + write `PLAN.md`).** Both pass; plan written to `PLAN.md`.

**Procedure 6 (review pass?).** Skipped: fully reversible, no external facts, one file. Exactly
the case where the optional pass is not worth the quota.

Note what the plan does *not* do — it does not plan the release announcement. Step 1's
falsifier could demote the whole item, so anything past it would be planning past a hard gate.
(`plugin.json` itself is owned by the packaging agent; this example only *reads* it.)

---

## Command verification

**Tier legend:** **T1** = safe/read-only — executed during authoring, real output pasted.
**T2** = dry-runnable (`--dry-run`). **T3** = mutating, destructive, or paid/OAuth provider
calls — never executed by an agent; health sentinels only, tagged `verified: manual <date>`.

| Command | Tier | Status |
|---|---|---|
| `/usr/local/bin/python3.11 -m pytest -q` | T1 | Executed 2026-07-29 → `35 passed in 1.69s` |
| `ace --help` | T1 | Executed 2026-07-29 → lists only `debt`, `run` (see Known limitations) |
| `~/.claude/scripts/adapters/ollama.sh --health` | T1 | Executed 2026-07-29 → `OLLAMA-OK (qwen2.5-coder:7b)` |
| `~/.claude/scripts/adapters/doctor.sh --fast` | T1 | Executed 2026-07-29 → `ALL SEATS HEALTHY` (agy skipped) |
| `openai.sh` / `agy.sh` real prompt | **T3** | `verified: manual 2026-07-29` — paid/OAuth. Health sentinels only: `OPENAI-OK (key valid; 119 models available)`, `AGY-OK (mode=argv)` |

Note the T1 discipline: exit 0 alone is not verification. `ace --help` exits 0 *and* proves the
globally installed CLI is stale — that is a finding, not a pass.

---

## Known limitations

- **No rebuttal round anywhere in ACE.** The optional review pass is one-shot; you never send
  the reviewer's objection back for a response. Known enhancement, not a launch blocker.
- **The globally installed `ace` (`/usr/local/bin/ace`) is behind this branch** — it exposes
  only `run` and `debt`, not `banner` or `memory`. `/ACE:plan` does not depend on the CLI, so
  this does not block it, but do not print `ace banner` output in a plan and claim it ran.
- **No step-quality scorer.** Whether a Falsifier actually falsifies is a human judgement here;
  nothing in the codebase checks it.
- **The 9-invocation demand figure for `/octo:plan`** is inherited from the migration audit and
  was not independently re-counted while writing this skill.

---

## Provenance and maintenance

| Fact | Source | Re-verify with |
|---|---|---|
| GOVERNOR/MIRROR modes and their menus | `ace/cli.py` | `grep -n 'MIRROR\|GOVERNOR\|Full Governor' ace/cli.py` |
| "Next falsifiable step" wording | `ace/cli.py` Governor synthesis menu | `grep -n 'falsifiable claim' ace/cli.py` |
| Weak-synthesis / incapacity-deference rationale | `ace/presets.py` module docstring | `sed -n '1,25p' ace/presets.py` |
| Coupling function definition | `ace/coupling/function.py` | `grep -n 'class CouplingFunction' ace/coupling/function.py` |
| Convergence warning fires in both modes | `ace/coupling/function.py:581`, `ace/agents/synthesis.py:149` | `grep -n 'def convergence_warning' ace/coupling/function.py` |
| preset → mode mapping | `ace/presets.py` | `/usr/local/bin/python3.11 -c "from ace.presets import PRESETS; [print(k, v.mode) for k,v in PRESETS.items()]"` |
| Adapter invocation contracts (stdin/argv, seats, PII rules) | `~/.claude/scripts/adapters/HARVEST.md` | `~/.claude/scripts/adapters/doctor.sh --fast` |
| agy fetches live sources (not training recall) | GATE-1 grounding probe, 2026-07-29: asked for `api.github.com/repos/ollama/ollama/releases/latest`, returned `v0.32.5`; independent fetch matched | Re-run the probe manually (T3) |
| Suite green | this branch | `/usr/local/bin/python3.11 -m pytest -q` |

**Date-stamped, expect drift:** provider health (2026-07-29), the 119-model OpenAI figure, the
stale global `ace` binary, and `ollama` model routing. Re-run `doctor.sh` at session start.

**Deeper material:** `references/cli-scaffolding.md` (when the `ace` CLI is worth adding to a
planning session, with the real flags), `references/decorrelated-review.md` (full review-pass
protocol, prompt variants, and how to write up a review that found nothing).
