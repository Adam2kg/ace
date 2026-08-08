---
name: ace-debug
description: >-
  Debug an observed fault in the USER'S system by diverging over root-cause hypotheses
  (cognitive frames on a strong model), then converging on the cheapest falsifying probe
  order — fix only after a hypothesis survives a probe. Use for "debug this", "why is X
  failing", "root cause this", "it worked yesterday", a pasted traceback / failing test /
  wrong output, "I'm stuck on this bug", "what could cause this", or "/ACE:debug".
  Boundary with the other ACE commands: /ACE:doctor checks ACE'S OWN provider seats (agy,
  ollama, openai) — if the broken thing is an ACE seat or an empty debate round, that is
  doctor, not debug. /ACE:debate critiques a decision or artifact; debug explains a
  malfunction. /ACE:plan sequences a settled decision; debug's probe ladder is not a plan —
  it is falsification ordering, and it ends the moment a hypothesis survives.
  Successor to the retired /octo:debug and /octo:skill-debug; those also match "debug
  this" — prefer ACE:debug; the Octopus versions dispatch to providers that no longer
  exist. Verified 2026-08-08.
---

# /ACE:debug — hypothesis divergence, falsification convergence

Debugging in ACE is two moves, in strict order:

1. **Diverge** over root-cause hypotheses — the failure mode this prevents is anchoring:
   the first plausible cause absorbs all attention and contradicting evidence gets
   explained away.
2. **Converge** by falsification — order probes by *discrimination-per-cost*, run the
   cheapest one that splits the hypothesis set, and let evidence kill branches.

**The governing rule: no fix before a hypothesis has survived a probe.** A fix applied on
an unfalsified hypothesis that happens to make the symptom vanish is the debugging
equivalent of a zombie seat — it reports healthy while proving nothing. If the symptom
disappears without you being able to say which hypothesis survived and how, record that
plainly: *symptom gone, cause unconfirmed*.

---

## When to use this — and when not to

| Situation | Command |
|---|---|
| A traceback, failing test, wrong output, or "worked yesterday" | `/ACE:debug` |
| An ACE seat returned nothing / a debate round is garbage | `/ACE:doctor` — that is ACE's own fleet, not the user's system |
| "Is this design right?" / critique an existing artifact | `/ACE:debate` |
| The cause is known and the user wants the fix sequenced | `/ACE:plan` |
| The "bug" is a usage error with a named exception from `ace run` itself | Triage table in `skills/ace-debate/SKILL.md` |

---

## The flow

### 1 — Intake (do not skip; hypotheses formed on a paraphrase inherit its errors)

Collect verbatim, not summarized: the exact error text or wrong-output pair
(expected vs observed), the reproduction command and its reliability (always /
intermittent), and **what changed** closest to onset (code, deps, config, environment,
data, time-of-day). If the user cannot say what changed, that is itself signal — widen
the environment frames.

### 2 — Hypothesis divergence (frames-on-Claude is the default engine)

Generate hypotheses across *distinct causal layers*, not variations of one layer: the
code itself, its inputs/data, dependencies and versions, configuration, environment and
resources, timing/concurrency, and the observer (the test or logging being wrong is a
hypothesis, not an insult). Aim for 4–7 genuinely distinct branches; label each with the
layer it lives on. This runs in the conversation — the external seat is an escalation
(step 5), not the baseline.

### 3 — Rank by discrimination-per-cost

For each hypothesis: what is the cheapest observation that would *kill* it? Prefer probes
that discriminate between several branches at once (a bisect, a version pin, a minimal
repro) over probes that merely confirm the favorite. State the expected observation
under each surviving hypothesis **before** running the probe — a probe whose outcome you
cannot predict per-branch discriminates nothing.

### 4 — The falsification ladder

Run probes cheapest-first. After each: name which hypotheses died, which survived, and
whether the surviving set warrants new branches. Two anti-patterns to refuse:

- **Shotgun fixing** — applying several candidate fixes at once. If the symptom clears,
  you have learned nothing and shipped superstition.
- **Confirmation laddering** — running only probes the favorite hypothesis predicts it
  will pass.

### 5 — Escalation to an external seat (optional, gated)

Dispatch the cross-family seat only when: two full ladder rounds left the set standing,
the favorite hypothesis keeps surviving probes *you designed under it* (self-anchoring
risk), or the fault is high-stakes (data loss, security, production). Before dispatch,
run `/ACE:doctor` if this session has not — a zombie seat's vacuous agreement is worse
here than anywhere, because "the other model also thinks it's the cache" feels like
confirmation. Aggregate asymmetrically per the ace-debate rules: the external seat's
**disagreement** (a hypothesis or layer you missed) is the entire value; its agreement
counts for nothing.

**Privacy rule:** logs and stack traces routinely embed PII, hostnames, keys, and
proprietary paths. If the material is privacy-bound, the only external seat is
`ollama` (and pin the model first — `export ACE_OLLAMA_MODEL=...`, see ace-doctor on the
first-row-of-`ollama list` default). Never paste privacy-bound material into `agy`.

### 6 — After the kill

State: the surviving hypothesis, the probe that confirmed it, the fix, and how the fix
was verified (the original repro command, re-run). If the user asked for diagnosis only,
stop after the surviving hypothesis — report, do not fix.

---

## Running the engine instead (optional)

The conversation is the default divergence engine. The CLI adds value when the user wants
the coupling machinery (attractor debt over deferred hypotheses across cycles):

```bash tier=T3
# Interactive synthesis-focus prompt fires each cycle (menu at ace/cli.py:421);
# in a non-interactive shell feed one choice per cycle on stdin or the run aborts
# AFTER quota is spent.
printf '2\n' | ace run "<symptom>" --preset debugging --providers agy
```

`--preset debugging` is Sonnet-divergence → Opus-synthesis, low noise ("follow a
hypothesis deep before pivoting"). Valid seats are `agy` and `ollama` only; an
all-unknown `--providers` list crashes with `ValueError` (triage: ace-debate SKILL).

---

## Graceful degradation

| Condition | Rule |
|---|---|
| agy down / quota out | Full ladder still runs — frames-on-Claude is the baseline, only cross-family decorrelation is lost. Say so once and continue |
| Privacy-bound material and ollama down | External escalation is unavailable, period. Frames-on-Claude only; never a cloud seat |
| Probe impossible (no repro, no access to the failing env) | Say which hypotheses are untestable and what access would unlock them — do not silently downgrade them to "unlikely" |

---

## Provenance

| Fact | Date verified | Tier | Re-verify with |
|---|---|---|---|
| `debugging` preset exists (Sonnet→Opus, low noise) | 2026-08-08 | T1 | `grep -n '"debugging"' ace/presets.py` |
| Engine ships exactly two runners `{agy, ollama}` | 2026-08-08 | T1 | `grep -n 'runners: dict' ace/agents/divergence.py` |
| Interactive synthesis-focus menu exists in `run` | 2026-08-08 | T1 | `grep -n 'Load-bearing' ace/cli.py` |
| Installed `ace` on PATH renders `banner` (post-unification) | 2026-08-08 | T3 (session-observed) | `ace banner --preset debugging` |

Volatile: the stdin menu numbering and seat names. Structural: the fix-after-survival
rule and the doctor/debate/plan boundaries.
