# The decorrelated review pass — full protocol

Long-tail detail for the optional external pass described in `SKILL.md`. Read this when you
have decided to fire the pass and want the exact prompt, the failure handling, and the write-up
rules. **This file is the single home for the three prompt variants** — `SKILL.md` points here
rather than duplicating them.

Tier codes (T1/T3) are defined in `SKILL.md` § *Command verification*.

Reminder of the governing constraint: **this is the only external involvement in `/ACE:plan`,
and it runs over a finished plan — never during drafting, and never as a vote.**

---

## Seat selection, expanded

| Seat | Family | What it is good for | What it is NOT for |
|---|---|---|---|
| `openai.sh` | OpenAI (different training family from Claude) | Decorrelated reasoning errors: unnamed assumptions, missing failure modes, ordering mistakes | Facts about the live world — it answers from training unless you give it the facts |
| `agy.sh` | Gemini family, Antigravity CLI | Factual currency: does this API/version/limit still exist? Verified to fetch live sources | Deep reasoning over your private codebase — it has no context you do not paste |
| `ollama.sh` | local Qwen 7B | Nothing in this command. Privacy-bound bulk work only | Judgement of any kind. See SKILL.md, "Why there is no second voice here" |
| `gpt-oss:120b-cloud` | cloud, reached through ollama | Fallback second opinion only | **Anything with PII or GDPR-bound data — it is cloud despite living in ollama** |

**One pass per risk, never a tally.** Most plans need exactly one seat. A plan that is both
hard to reverse *and* dependent on external facts may take one `openai.sh` reasoning pass and
one `agy.sh` currency pass — they answer different questions. What is forbidden is *comparing*
them: two seats saying the same thing is still worth nothing, because agreement carries no
weight under the asymmetric aggregation rule.

---

## Prompt variants

All are T3 (paid/OAuth). The adapters take the prompt on stdin or as `$1`.

### Variant A — reasoning review (default, `openai.sh`)

```bash tier=T3 verified=2026-07-29
# T3
{
  printf '%s\n\n' "Review this execution plan. Do not rewrite it. Report only: (1) steps whose stated Falsifier would not actually falsify them, (2) load-bearing assumptions the plan never names, (3) any factual claim you believe is out of date. Cite the step number for each point. If you have nothing to report for a category, say 'none' — do not pad."
  cat PLAN.md
} | ~/.claude/scripts/adapters/openai.sh
```

### Variant B — factual currency (`agy.sh`)

```bash tier=T3 verified=2026-07-29
# T3
{
  printf '%s\n\n' "This plan makes claims about external systems (APIs, versions, limits, pricing). Check each such claim against current sources and report ONLY the ones that are wrong or stale, with the source you checked. Ignore everything internal to the author's codebase."
  cat PLAN.md
} | ~/.claude/scripts/adapters/agy.sh || echo 'REVIEW PASS FAILED — no output'
```

> **⚠ `agy.sh` has no empty-output gate.** Its run path (`agy.sh:62–70`) execs the binary and
> passes agy's own exit code straight through with no content check — only `health()` matches a
> sentinel. An empty agy reply therefore arrives as **exit 0 and silence**, which is the
> original zombie. `openai.sh` (line 53) and `ollama.sh` do fail on empty content; agy does not.
> On this variant you must apply the on-topic test below by hand.

### Variant C — ordering only (cheap, either seat)

```bash tier=T3 verified=2026-07-29
# T3
{
  printf '%s\n\n' "For this plan, answer one question: is any step ordered later than a step whose falsifier could invalidate it? List only the offending pairs as 'Step N before Step M, because ...'. If none, reply 'ordering ok'."
  cat PLAN.md
} | ~/.claude/scripts/adapters/openai.sh
```

Variant C is the highest signal-per-token of the three, because ordering errors are the
failure mode a single author is worst at catching in their own plan.

---

## Reading the result

Apply the asymmetric aggregation rule mechanically:

| Reviewer said | You do |
|---|---|
| "The plan looks solid" | **Nothing.** Do not record it. Do not raise your stated confidence. Do not cite it as validation. |
| "Step 4's falsifier doesn't falsify it" | Re-derive that step yourself. If your re-derivation holds, the plan stands and you note the objection as considered-and-rejected with a reason. |
| "Step 2 assumes X, which is never stated" | Almost always correct and cheap to fix — name the assumption and give it a falsifier or its own step. |
| "The API you cite was removed in v3" | Verify independently before acting. A different-family model is a *flag generator*, not a source of truth. |
| Empty output / non-zero exit | **You got no review.** Report that plainly. Do not describe the plan as reviewed. Remember `agy.sh` reports empty output as exit 0 — check the content, not just `$?`. |
| Fluent output that never mentions a step number | Treat as suspect — likely off-topic generation. Same handling as empty. |

**Never** let a reviewer's objection rewrite the plan directly. The strong model re-derives;
the plan changes only when the re-derivation changes.

---

## The zombie gate, applied here

The governing exhibit (from the ACE migration audit): a debate round file was found on disk
byte-identical to a `.err` file containing a Gemini `IneligibleTierError` stack trace — and it
had been filed as a legitimate debate round. Non-empty checks, `size > 500B` checks, and
`file exists` checks all pass on that file.

So the acceptance test for a review result is **on-topic content**, not presence:

- Does the response reference at least one step number from the plan?
- Does it contain a claim that is specific to *this* plan, not generic advice?

If either answer is no, the seat produced nothing usable. Record the pass as FAILED and either
retry once or proceed without it — but say which.

Health sentinels for the two review seats (`verified: manual 2026-07-29` — do not re-run
speculatively, they cost quota):

```
$ ~/.claude/scripts/adapters/openai.sh --health
OPENAI-OK (key valid; 119 models available)

$ ~/.claude/scripts/adapters/agy.sh --health
AGY-OK (mode=argv)
```

---

## Writing up a review that found nothing

This is where overselling creeps in. The honest write-up is:

> Decorrelated review pass: one `openai.sh` pass over the finished plan (variant A). Returned
> two objections, both re-derived and rejected (Step 3's falsifier is observable at staging;
> Step 5's "unnamed assumption" is stated in the decision restatement). No changes made. The
> reviewer's agreement with the remaining steps is **not** evidence and is not counted.

The dishonest write-up — the one to avoid — is *"the plan was validated by a second model."*
It was not. Nothing here validates anything; the pass can only ever raise flags.

---

## Known gap

There is **no rebuttal round**. You never send the reviewer's objection back for a response,
and the reviewer never sees your re-derivation. This is a real limitation of the current
design, shared with `/ACE:debate`, and is a known enhancement rather than a defect to hide.
