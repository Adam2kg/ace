---
name: ace-review
description: >-
  Cross-family decorrelated review of a CONCRETE DIFF, branch, or PR — the escalation
  path beyond Claude-native review, used when the change is high-stakes enough that
  Claude reviewing alone leaves a shared-blind-spot risk worth paying to reduce. Use for
  "review this with another model", "second opinion on this diff/PR", "cross-family
  review", "escalate the review", "have agy look at this change", or "/ACE:review".
  NATIVE-FIRST RULE: for an ordinary review request ("review my changes", "check this
  PR") prefer Claude-native /code-review — it is cheaper, inline-comment-capable, and
  sufficient for most diffs; this skill ADDS one decorrelated pass on top, it does not
  replace the native review. Boundary with /ACE:debate: debate owns critique of designs,
  RFCs, plans, and threat models (prose artifacts); review owns code diffs. If the user
  points at a document, route to debate; if at a diff, stay here.
  Successor to the retired /octo:review, /octo:skill-code-review and /octo:staged-review;
  those also match "review this" — prefer ACE:review; the Octopus versions dispatch to
  providers that no longer exist. Verified 2026-08-08.
---

# /ACE:review — decorrelated diff review

One reviewer family has one error distribution. A second Claude pass re-samples the same
distribution — that is the "sophisticated echo" failure: agreement quality without
decision quality. This skill exists for exactly one increment: **an independent
training-family look at the load-bearing hunks of a diff**, aggregated asymmetrically.

It is an *escalation*, not a default. The cost side is real (quota, latency, and code
leaving the box — see the privacy gate), so it must be justified by stakes: migrations,
auth/crypto/money paths, data-loss surfaces, concurrency, public API breaks.

---

## When to use this — and when not to

| Situation | Command |
|---|---|
| Ordinary "review my changes / this PR" | Claude-native `/code-review` — stop here for most diffs |
| High-stakes diff, wants an independent second family | `/ACE:review` (this skill) |
| Critique a design doc, RFC, plan, threat model | `/ACE:debate` (`--preset frames-adversarial`) |
| "Is the review seat even alive?" | `/ACE:doctor` |
| Review found the bug, now sequence the fix | `/ACE:plan` |

---

## The flow

### 1 — Native pass first

Run the Claude-native review (or ingest one the user already has). The native pass finds
the bulk; the external seat is not for bulk — it is for what the native pass is
structurally blind to.

### 2 — Select the escalation set (never ship the whole diff to the seat)

From the diff, pick the **load-bearing hunks**: the 1–5 places where being wrong is
expensive — state machines, boundary arithmetic, auth checks, migration steps, lock
ordering, error paths. Escalating everything buries the seat's attention and multiplies
the privacy surface for no decorrelation gain.

### 3 — Privacy gate (before any byte leaves the box)

`agy` is a cloud seat. Sending code to it is sending code to a third party. Confirm with
the user once per session that this diff may leave the box; for proprietary or
PII-adjacent code the external options are `ollama` (pin the model first — see
ace-doctor on the first-row default) or nothing — an adversarial frames pass on Claude
in this conversation. Never decide silently that code is "probably fine to send".

### 4 — The decorrelated pass

Doctor first if the session has not (`/ACE:doctor` — a zombie seat's empty "LGTM" is the
worst possible review outcome: vacuous agreement counted as a clean bill). Then send each
selected hunk with a **refutation prompt** — instruct the seat to find what is wrong,
never to approve: concrete failure scenario, input, or interleaving. An approval from a
seat asked to refute carries some information; an approval from a seat asked to review
carries none.

### 5 — Aggregate asymmetrically (the rule that makes this trustworthy)

- The seat's **disagreement** (a claimed defect) is a flag to re-examine with the strong
  model — verify it against the actual code before reporting; external findings are
  candidates, not conclusions.
- The seat's **agreement counts for nothing.** Never report "both models approved" as a
  safety claim, and never let a seat's approval overturn a native-pass finding.
- Report findings by content ("the migration drops rows where…"), never by tally.

### 6 — Output

Merge into a single findings list: confirmed items first, each with file:line and a
concrete failure scenario; then unverified external candidates, labeled as such. State
explicitly which hunks got the decorrelated pass and which did not — a partial
escalation reported as a full one is a silent-truncation lie. Do not post PR comments or
push anything without the user's confirmation.

---

## The engine's `design-review` preset (know why this skill does NOT default to it)

`--preset design-review` exists in the engine (Haiku-divergence → Sonnet-synthesis,
"fast variation, consistency tracking"). It is tuned for *many small cheap looks*, which
suits checking a batch of small changes — not for the high-stakes single-diff case this
skill exists for, where a weak divergence model would defer from incapacity. If the user
wants the batch mode:

```bash tier=T3
# Interactive synthesis-focus prompt fires each cycle; feed one choice per cycle
# on stdin in non-interactive shells or the run aborts AFTER quota is spent.
printf '2\n' | ace run "<review scope>" --preset design-review --providers agy
```

---

## Graceful degradation

| Condition | Rule |
|---|---|
| agy down / quota out | Run the adversarial frames pass on Claude and say plainly: **no independent second opinion was available** — Claude re-reviewing Claude is not decorrelation |
| Privacy gate fails (code may not leave the box) and ollama down | Native review + frames-on-Claude only. Never a cloud fallback |
| Seat output empty or off-topic | That hunk got **no** decorrelated pass — treat as unreviewed-by-seat, never as approved (zombie gate) |

---

## Provenance

| Fact | Date verified | Tier | Re-verify with |
|---|---|---|---|
| `design-review` preset exists (Haiku→Sonnet) | 2026-08-08 | T1 | `grep -n '"design-review"' ace/presets.py` |
| Engine ships exactly two runners `{agy, ollama}` | 2026-08-08 | T1 | `grep -n 'runners: dict' ace/agents/divergence.py` |
| `ace banner` availability rows are PATH-lookup only | 2026-08-08 | T1 | `grep -n 'shutil.which' ace/cli.py` |
| Claude-native `/code-review` available in this environment | 2026-08-08 | session-observed | skill listing |

Volatile: seat names, native-review command name. Structural: native-first routing, the
privacy gate, refutation prompting, and asymmetric aggregation.
