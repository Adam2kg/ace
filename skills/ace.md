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

If user picks Mirror + no calibration: default to Explorer (`--preset human-adhd --human-mode`).

### Step 3 — Check providers and display banner

```bash
printf "codex:%s\n" "$(command -v codex >/dev/null 2>&1 && echo available || echo missing)"
printf "gemini:%s\n" "$(command -v gemini >/dev/null 2>&1 && echo available || echo missing)"
```

Display banner (MANDATORY before running):
```
🐙 ACE — [MIRROR | GOVERNOR] mode — [Calibration label]
🔴 Codex: [available ✓ / not installed ✗] — divergence (technical branches)
🟡 Gemini: [available ✓ / not installed ✗] — divergence (lateral branches)
🔵 Claude: available ✓ — synthesis (trajectory maintenance)
```

### Step 4 — Run

```bash
ace run "<topic>" --preset <preset> [--human-mode] [--cycles N]
```

If `ace` CLI is not available:
```bash
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
*Tuning decision: add a coherence floor (~0.70) for grounded/technical topics. See*
*"Open tuning items" below. For now, prefer Deep Focus on concrete engineering tradeoffs.*

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
*Known limitation: with only one live divergence provider (e.g. codex quota-exhausted,*
*gemini only), this fires on single-source bias rather than genuine cross-provider*
*monoculture. Treat the warning as low-signal when fewer than 2 providers are live.*
*Tuning decision: gate firing on ≥2 live providers. See "Open tuning items".*

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

### "Every branch feels like the same idea from a different angle"

Frame monoculture. ACE should have warned. If it didn't fire:
- Check if `--preset` is a human-mode preset (monoculture detection is always active)
- Add a different seed topic next cycle: "What would someone who DISAGREES with all of this say?"
- Try `--preset frames-adversarial` for one cycle to force perspective diversity

### "The synthesis panel is useless / feels like noise"

Two causes:
1. **Too many branches** — reduce `--cycles` or pick focus option [1] or [3] instead of [4]
2. **Wrong calibration** — Explorer for scattered thinking, Deep Focus for precision work. If you're in Deep Focus during open-ended exploration, synthesis will try to converge prematurely.

### "ACE keeps warning about overthinking but I'm not looping"

The overthinking warning fires when ≥2 branches have been visited ≥3 times with stagnant
progress delta (< 0.08) across all recent visits. If this fires on genuine deepening:
- This is a calibration gap — Explorer uses a lower depth delta floor (0.15) to better
  distinguish deepening from looping
- Switch to Explorer or set `--preset human-adhd` explicitly
- *Still pending — the one calibration run (2 cycles) never triggered re-emergence, so the*
  *0.08 stagnation threshold is untested. Needs a ≥4-cycle run with deliberate revisiting.*

### "Nothing is getting deferred / attractor debt is always 0"

This means all branches are being integrated immediately — coupling function isn't accumulating
anything. Two causes:
1. Topic is genuinely well-bounded (good)
2. Budget is too high and the coupling function never needs to defer anything — try reducing
   `--cycles` or use `--preset debugging` for tighter budget

### "The coupling state shows high deferred_count but nothing is surfacing"

Debt threshold is too high for the session. Adjustable:
```bash
ace run "<topic>" --preset human-adhd --debt-threshold 1.5 --human-mode
```
Or use Deep Focus which has a threshold of 6.0 (patient); Explorer uses 2.0 (reactive).

---

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
```bash
cd ~/ace && pip install -e .
```

---

## Open tuning items

Resolved from the first live Mirror calibration run (2 cycles, 360-editor decision).
These are agreed code changes not yet implemented — tracked here so they aren't lost.

| # | Item | Verdict | Change | Status |
|---|------|---------|--------|--------|
| 1 | Frame-monoculture detector | TUNE | Gate firing on ≥2 live divergence providers; with one provider the signal conflates source bias with structural monoculture | **code TODO** in `frame_monoculture_risk` |
| 2 | Synthesis focus menu | VALIDATED | Keep all four options — focused panels beat the full dump | done (no change) |
| 3 | Overthinking warning | KEEP-PENDING | Needs a ≥4-cycle run with deliberate revisiting to test the 0.08 stagnation threshold | awaiting run |
| 4 | Explorer coherence floor | TUNE | Add a coherence floor (~0.70) for grounded/engineering topics so novelty can't drown actionability | **code TODO** in scoring/preset |

**Blocker for the code TODOs:** there is no test suite for `ace/coupling/function.py`. Both
behavioral changes (provider-gated monoculture, coherence floor) should land with unit tests
rather than being tuned blind off a single run.
