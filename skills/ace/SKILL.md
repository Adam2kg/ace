---
name: ace
version: 0.1.0
description: Cognitive-divergence CLI for Mirror mode (human thinking scaffold) and Governor mode (AI thinking scaffold)
---

# /ace — Asymmetric Cognitive Equilibrium

Run an ACE session: the coupling function scaffolds a thinking process — either your own
(MIRROR mode) or an AI's (GOVERNOR mode).

**The coupling function — not the agents — is the primary design object.**

ACE is not a chatbot. It generates focused prompts. Claude Code is the synthesis engine.
The paste-cycle-loop is the primary UX.

---

## Instructions for Claude

### Step 1 — Ask mode and calibration (MANDATORY, before running anything)

**You MUST use AskUserQuestion before invoking the CLI.**

```javascript
AskUserQuestion({
  questions: [
    {
      question: "Are you actively contributing ideas to this session?",
      header: "Mode",
      multiSelect: false,
      options: [
        {
          label: "Yes — Mirror mode (human thinking scaffold)",
          description: "You ARE the thinking engine. ACE amplifies your branches, catches drift, and asks questions you won't ask yourself. The synthesis panel is a prompt you paste into Claude Code to reflect on — not a summary."
        },
        {
          label: "No — Governor mode (AI thinking scaffold)",
          description: "AI providers generate all branches. ACE drives the trajectory toward resolution. You read the synthesis and decide the next move."
        }
      ]
    },
    {
      question: "Which calibration should ACE use?",
      header: "Calibration",
      multiSelect: false,
      options: [
        {
          label: "Explorer (Recommended for Mirror mode)",
          description: "Broad-scan. High interrupt budget (8), low closure pressure. AI catches drift and provides closure. Good for open-ended problems, decisions with many unknowns, or when you're feeling scattered. Preset: human-adhd."
        },
        {
          label: "Deep Focus",
          description: "Narrow-channel depth. Low interrupt budget (3), moderate closure pressure. Protects sustained attention. Good for precision work, single-topic deep dives, or when switching is costly. Preset: human-scientific."
        },
        {
          label: "Architecture",
          description: "Governor mode: synthesis-heavy. Sonnet divergence + Opus synthesis. Human provides divergence; AI provides trajectory depth. Best for design and creative work."
        },
        {
          label: "Debugging",
          description: "Governor mode: follow a hypothesis deep before pivoting. Low noise. Best for fault-tree work and root cause analysis."
        }
      ]
    }
  ]
})
```

### Step 2 — Map answer to CLI flags

| Mode answer | CLI flag |
|-------------|----------|
| Mirror | `--human-mode` |
| Governor | (omit) |

| Calibration answer | CLI flag |
|-------------------|----------|
| Explorer | `--preset human-adhd` |
| Deep Focus | `--preset human-scientific` |
| Architecture | `--preset architecture` |
| Debugging | `--preset debugging` |
| Design review | `--preset design-review` |
| Looping / repetitive | `--preset looping` |
| frames-deep (via "Other") | `--preset frames-deep` |
| frames-adversarial (via "Other") | `--preset frames-adversarial` |

The frames presets (`frames-deep`, `frames-adversarial`) are frames-only: single
provider + cognitive frames, **no external-provider dispatch**. Offer them when the
user mentions budget/quota limits, conceptual work, or threat modeling — they can be
selected through the "Other" free-text option in Step 1.

If user picks Mirror + no calibration: default to Explorer (`--preset human-adhd --human-mode`).

### Step 3 — Display banner (MANDATORY before running)

The engine renders its own banner — coupling, models, frames mode, and **live**
provider availability. Run it and show its output to the user verbatim:

```bash tier=T1
cd ~/ace-unify && /usr/local/bin/python3.11 -m ace.cli banner --preset architecture
```

> ⚠️ **Use the module form above, not bare `ace banner`.** Verified 2026-07-29: the
> globally installed `/usr/local/bin/ace` is **stale** — it exposes only `run` and
> `debt`, so `ace banner` exits 2 with `No such command 'banner'`. The repo's
> `ace/cli.py` does define `banner`. Until the install is refreshed
> (`cd ~/ace && pip install -e .`, T3), always invoke via `python3.11 -m ace.cli`.
> Note also that system `python3` is 3.9 and **cannot** import this package — use
> `/usr/local/bin/python3.11`.

- For `frames-deep` / `frames-adversarial` it prints NO external-provider rows
  (frames-only presets do no multi-provider dispatch) — do not add any.
- For all other presets it prints one row per active provider (default `agy`:
  🧭 agy) plus the 🔵 Claude synthesis row.
- **The fleet was pruned on 2026-07-29.** `codex` (quota-dead, exit 137) and the
  `gemini` CLI (retired) were **deleted** from the engine — there is no runner for
  either. The only divergence runners are `_run_agy` and `_run_ollama`. Never render
  a Codex or Gemini row; passing `--providers codex` or `--providers gemini` now
  yields no runner. See the sibling skill `ace-doctor` for seat health.

**Render statuses ONLY from command output. Never infer, guess, or hand-write a
provider availability row — if a provider isn't in the output, it doesn't get a row.**

**Fallback** (only if the `ace` CLI itself is missing — see Step 4): build the banner
from these two commands and NOTHING else. Both mirror the engine exactly; do not
paraphrase or fill gaps from memory.

1. Provider availability — render rows ONLY from this output:

```bash tier=T1
printf "agy:%s\n"    "$(command -v agy    >/dev/null 2>&1 && echo present || echo missing)"
printf "ollama:%s\n" "$(command -v ollama >/dev/null 2>&1 && echo present || echo missing)"
```

> ⚠️ **`command -v` proves PRESENCE, not health — this is the zombie gate.** A binary
> that exists but has dead auth returns empty output while reporting "available", and
> that vacuous silence can be miscounted as agreement. For a real health check that
> verifies actual on-topic output, use `ace-doctor` (`~/.claude/scripts/adapters/doctor.sh`).
> Use the probe below only as a last-resort fallback when the `ace` CLI itself is missing.

2. Preset coupling — read from the engine's presets, never hand-write model names
   (append `p = apply_human_mode(p)` after `get_preset` when human-mode is active):

```bash tier=T1
/usr/local/bin/python3.11 -c "
import sys, os; sys.path.insert(0, os.path.expanduser('~/ace'))
from ace.presets import get_preset, apply_human_mode
p = get_preset('architecture')   # substitute the user's chosen preset
print(f'frames_only:{p.frames_only}')
print(f'frames_set:{p.frames_set}')
print(f'divergence_model:{p.divergence_model}')
print(f'synthesis_model:{p.synthesis_model}')
print(f'synthesis_strength:{p.synthesis_strength}')
"
```

Then assemble:

- If `frames_only:True` → show
  `Divergence: {divergence_model} (frames-{frames_set}) — single provider, cognitive frames`
  and NO provider rows (step 1's output is irrelevant; discard it).
- Otherwise → one row per active provider (default `agy`) with status from step 1,
  then `Divergence: {divergence_model} (agy) + cognitive frames` and
  `Synthesis: {synthesis_model} (strength {synthesis_strength}/5)`.
- Add an `ollama` row only when the user explicitly passes `--providers ...,ollama`
  (local seat; see `ace-debate` for why a local model is never a debate peer).

### Step 4 — Run

```bash tier=T3 verified=2026-07-29
ace run "<topic>" --preset <preset> [--human-mode] [--cycles N]
```

If `ace` CLI is not available:
```bash tier=T3 verified=2026-07-29
cd ~/ace && pip install -e .
```

Default cycles: 1 for a quick pulse, 2–3 for a proper session.

### Step 5 — The paste-cycle-loop (Mirror mode)

After each cycle, ACE shows:
1. **Branch list** — the divergent threads it generated
2. **Warnings** (if any) — frame monoculture, overthinking, depth attractor
3. **Synthesis focus menu**:
   ```
   [1] Tensions — surface unexpected connections (do NOT resolve)
   [2] Hidden question — what question none of these raises alone?
   [3] Uncomfortable branch — which one is hardest to hold open?
   [4] Full Mirror — all of the above (default)
   ```
4. **Panel** — a focused prompt to paste into Claude Code

**What to do:**
- Pick a focus number (or Enter for Full Mirror)
- Copy the blue panel
- Paste it into this Claude Code conversation
- Read what comes back — sit with it, don't rush to act
- Run another cycle if you have more material

**After you read the synthesis response:**
- Ask: did this shift anything? If yes, run another cycle with the new framing.
- Ask: did this feel resolved? If yes, you're done.
- Ask: did this feel like noise? Lower `--cycles` next time or switch to Deep Focus.

### Step 6 — After the run (Governor mode)

- Surface convergence warnings (if AI divergence budget was unused = system failure, not success)
- Show attractor debt if branches were deferred
- Ask if the user wants another cycle or to adjust `--synthesis-strength`
- Present the synthesis panel for Claude Code integration

---

## Two modes, two optimization targets

| | MIRROR | GOVERNOR |
|--|--------|---------|
| **Who thinks** | Human | AI |
| **AI role** | Amplifier + reflection scaffold | Primary divergence + trajectory engine |
| **Synthesis goal** | Maximize productive entropy; ask the uncomfortable question | Minimize entropy; converge on load-bearing insight |
| **Convergence warning** | Suppressed — you agreeing is healthy | Active — AI agreeing with itself is failure |
| **Overthinking warning** | Active — circular revisiting detected | Not applicable |
| **Depth attractor** | Positive signal (genuine deepening) | Not tracked |

These are **anti-correlated** optimization targets. The coupling function maintains separate state for each.

---

## Calibrations (human-mode presets)

The axis is **attentional topology** — breadth vs depth — not task domain.
Pick based on how you're thinking right now, not what you're thinking about.

### Explorer (`--preset human-adhd`)

*Partially calibrated (1 live Mirror run). Budget/debt/resonance params unchanged.*
*Known limitation: on **grounded engineering decisions** Explorer over-optimizes novelty —*
*observed branches at novelty ~0.90 / coherence ~0.50 (metaphor-heavy, low actionability).*
*Explorer leaves the coherence floor off by design (novelty is the point). For grounded*
*work use Deep Focus (floor 0.70) or pass `--coherence-floor 0.70`. See "Tuning items" (#4).*

- Interrupt budget: 8 (short attention cycles; switching is natural)
- Debt threshold: 2.0 (surface deferred branches fast, before WM decay)
- Resonance weight: 0.80 (interest-based attention; resonance is the engagement lever)
- Closure pressure: 0.20 (AI handles closure; don't interrupt mid-flow)
- Depth delta floor: 0.15 (hyperfocus deepening may be compact but genuine)

Use when: open-ended exploration, decisions with many unknowns, feeling scattered,
starting something new, or when the blank page is the enemy.
**Not** for concrete engineering triage — use Deep Focus there.

### Deep Focus (`--preset human-scientific`)

*Calibration pending — design intent, not observed use.*

- Interrupt budget: 3 (topic switches are expensive; protect deep work)
- Debt threshold: 6.0 (stable WM can hold a large deferred queue)
- Resonance weight: 0.40 (domain-governed motivation; resonance matters but is stable)
- Closure pressure: 0.65 (gentle nudge — monotropic users can spiral on precision)
- Depth delta floor: default 0.20

Use when: precision work, single-topic deep dives, structured analysis,
or when interruption is costly.

---

## Synthesis focus options explained

*Validated (1 live Mirror run): the single-focus panels were noticeably tighter and*
*more useful than the old "full dump". The menu's complexity is justified — keep all four.*

These are the choices presented at end of each Mirror-mode cycle:

| # | Option | What it does | When to pick it |
|---|--------|-------------|-----------------|
| 1 | **Tensions** | Surfaces conflicts and unexpected connections. Does NOT resolve. | You sense something is in tension but can't articulate it |
| 2 | **Hidden question** | Finds the question the branches raise together that none raises alone | You want the meta-insight, not the content |
| 3 | **Uncomfortable branch** | Names the branch that's hardest to leave unresolved and explains why | You're avoiding something; you need to know what |
| 4 | **Full Mirror** (default) | All three above | General session; let the synthesis decide what matters |

Governor mode has its own menu: Trajectory update / Load-bearing vs noise / Next falsifiable step / Full Governor.

---

## Key concepts

**Attractor debt** — when the coupling function defers the same class of branch repeatedly,
debt accumulates as gravitational pull. When it exceeds the threshold (preset-dependent),
ACE surfaces those branches for mandatory re-examination.
High debt = trajectory is being warped by invisible pressure.

**Frame monoculture** — fires when > 80% of weighted branches share the same frame.
Warning: *"Frame monoculture detected — all branches use [domain] framing.
A perspective shift might reveal what this frame hides."*
This is a structural warning, not a content warning.
*Now gated on provider count: with fewer than 2 live divergence providers (e.g. agy*
*quota-exhausted, leaving ollama alone) the warning is suppressed, since one provider's framing*
*bias can't be distinguished from genuine cross-provider monoculture. Always active in*
*frames-only mode, where diversity is frame-based. See "Tuning items — resolved" (#1).*

**Depth attractor signal** (Mirror mode) — positive signal when a branch is genuinely
deepening across visits (not just being re-visited). ACE promotes it, does not warn.
Contrast with overthinking warning (circular visits with stagnant delta < 0.08).

**Convergence warning** (Governor mode) — AI synthesis agreeing with everything + unused
divergence budget = the synthesis agent has been captured by its own frame.
System failure. Not suppressed in Governor mode.

**Sophisticated echo** — symmetric Opus/Opus coupling optimizes for agreement quality,
not decision quality. Two Opus instances share priors and miss correlated blind spots.
This is why synthesis-heavy beats symmetric for architecture work.

**Relational context** — the coupling history from THIS session's agents.
Not portable. Use `--state-file` to persist and inspect between sessions.

---

## Preset table (AI-mode / Governor presets)

These come from a 3-round multi-provider debate.

| Task | Divergence | Synthesis | Debt threshold | Why |
|------|-----------|-----------|---------------|-----|
| Architecture | Sonnet | Opus | 2.5 | Human IS the divergence engine; AI synthesis depth is what's missing |
| Debugging | Sonnet | Opus | 3.0 | Follow a hypothesis to depth; synthesis ranks hypotheses |
| Design review | Haiku | Sonnet | 2.5 | Fast cheap variation + consistency tracking |
| Looping | Haiku | Sonnet | 5.0 | Haiku/Haiku loses trajectory; Sonnet synthesis prevents that cheaply |

**Synthesis-strength knob (1–5):** If a session feels too convergent, raise it.
If synthesis can't keep up with branches, lower it.
Default: 4 (architecture), 3 (debugging), 2 (design-review), 1 (looping).

---

## Diagnosing misbehavior

Symptom-driven diagnosis for **session behavior** — "every branch feels the same"
(frame monoculture), "synthesis is noise", "overthinking warning won't stop",
"attractor debt is always 0", "deferred_count high but nothing surfaces" — is in
[`references/session-diagnosis.md`](references/session-diagnosis.md).

For **provider seat** problems (a seat is down, auth dead, quota exhausted, or
returning empty output while reporting available) use the sibling skill
`ace-doctor` — that is a different failure domain and it owns the zombie gate.

## CLI reference

```
ace run TOPIC [OPTIONS]

Arguments:
  TOPIC         What the session is thinking about. Quote multi-word topics.

Options:
  --preset      Coupling preset. Default: architecture.
                Choices: human-adhd, human-scientific, human-creative,
                         architecture, debugging, design-review, looping,
                         frames-deep, frames-adversarial
  --human-mode  Activate Mirror mode. AI amplifies your thinking instead of
                driving it. Suppresses convergence warnings.
  --cycles N    Number of divergence-synthesis cycles. Default: 1.
  --state-file  Path to persist coupling state across sessions.
  --help        Show this message and exit.

Exit codes:
  0  Session completed normally
  1  User error (bad arguments, unknown preset)
  2  System error (provider unavailable, coupling function failure)
```

If `ace` CLI is not found:
```bash tier=T3 verified=2026-07-29
cd ~/ace && pip install -e .
```

---

## Tuning items — resolved

Historical calibration decisions (frame-monoculture gating, synthesis focus menu,
overthinking threshold, coherence floor) live in
[`references/tuning-history.md`](references/tuning-history.md).
