# /ace — Asymmetric Cognitive Equilibrium

Run an ACE session: divergence agents (🔴🧭) generate branches in parallel,
the synthesis agent (🔵) integrates via the coupling function.

The coupling function — not the agents — is the primary design object.

---

## Instructions for Claude

### Step 1 — Ask preset and mode (MANDATORY, before running anything)

**You MUST use AskUserQuestion to ask both questions before invoking the CLI.**
Do not default silently. The preset recommendation comes from a 3-round multi-provider debate.

```javascript
AskUserQuestion({
  questions: [
    {
      question: "Which coupling preset should we use?",
      header: "Preset",
      multiSelect: false,
      options: [
        {
          label: "Architecture (Recommended)",
          description: "Sonnet divergence + Opus synthesis — synthesis-heavy. Debate winner for creative/design work. Human provides the divergence; AI provides trajectory depth."
        },
        {
          label: "Debugging",
          description: "Sonnet divergence + Opus synthesis — follow a hypothesis deep before pivoting. Low noise. Debate winner for fault-tree work."
        },
        {
          label: "Design review",
          description: "Haiku divergence + Sonnet synthesis — fast variation, consistency tracking. Good for checking many small changes."
        },
        {
          label: "Looping / repetitive",
          description: "Haiku divergence + Sonnet synthesis — throughput mode. Haiku/Haiku would lose trajectory; Sonnet synthesis prevents that cheaply."
        }
      ]
    },
    {
      question: "Are you actively contributing ideas to this session?",
      header: "Human mode",
      multiSelect: false,
      options: [
        {
          label: "Yes — human-in-the-loop",
          description: "You ARE the divergence engine. AI divergence drops a tier and amplifies your ideas instead of competing with them. Convergence warnings suppressed."
        },
        {
          label: "No — AI-only divergence",
          description: "AI providers (Codex, agy) generate the branches. Standard coupling dynamics."
        }
      ]
    }
  ]
})
```

### Step 2 — Map answer to CLI flags

| Preset answer | CLI flag |
|--------------|----------|
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

| Human mode answer | CLI flag |
|------------------|----------|
| Yes | `--human-mode` |
| No | (omit) |

### Step 3 — Display banner (MANDATORY before running)

The engine renders its own banner — coupling, models, frames mode, and **live**
provider availability. Run it and show its output to the user verbatim:

```bash
ace banner --preset <preset> [--human-mode]
```

- For `frames-deep` / `frames-adversarial` it prints NO external-provider rows
  (frames-only presets do no multi-provider dispatch) — do not add any.
- For all other presets it prints one row per active provider (default
  `codex,agy`: 🔴 Codex, 🧭 agy) plus the 🔵 Claude synthesis row.
- Gemini (🟡) is legacy/deprecated — it appears only if the user explicitly adds
  it via `--providers ...,gemini`. Do not surface it otherwise.

**Render statuses ONLY from command output. Never infer, guess, or hand-write a
provider availability row — if a provider isn't in the output, it doesn't get a row.**

**Fallback** (only if the `ace` CLI itself is missing — see Step 4): build the banner
from these two commands and NOTHING else. Both mirror the engine exactly; do not
paraphrase or fill gaps from memory.

1. Provider availability — render rows ONLY from this output:

```bash
printf "codex:%s\n" "$(command -v codex >/dev/null 2>&1 && echo available || echo missing)"
printf "agy:%s\n"   "$(command -v agy   >/dev/null 2>&1 && echo available || echo missing)"
printf "gemini:%s\n" "$(command -v gemini >/dev/null 2>&1 && echo available || echo missing)"
```

2. Preset coupling — read from the engine's presets, never hand-write model names
   (append `p = apply_human_mode(p)` after `get_preset` when human-mode is active):

```bash
python3 -c "
import sys, os; sys.path.insert(0, os.path.expanduser('~/ace'))
from ace.presets import get_preset, apply_human_mode
p = get_preset('<preset>')
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
- Otherwise → one row per active provider (default `codex,agy`) with status from
  step 1, then `Divergence: {divergence_model} (codex, agy) + cognitive frames` and
  `Synthesis: {synthesis_model} (strength {synthesis_strength}/5)`.
- Gemini row only if the user explicitly adds gemini to `--providers`.

### Step 4 — Run

```bash
ace run "<topic>" --preset <preset> [--human-mode] [--cycles N]
```

If `ace` CLI is not available:
```bash
cd ~/ace && pip install -e .
```

### Step 5 — After the run

- Surface any convergence warnings (unless human-mode, where they're suppressed)
- Show attractor debt if any branches were deferred
- Ask if the user wants another cycle or to adjust the synthesis-strength knob

---

## Preset recommendations from debate

These come from a 3-round multi-provider debate (Gemini CLI + Claude Sonnet subagent + Claude moderator).

| Task | Winner | Divergence | Synthesis | Why |
|------|--------|-----------|-----------|-----|
| Architecture | synthesis-heavy | sonnet | opus | Human IS the divergence engine; AI synthesis depth is what's missing |
| Debugging | synthesis-heavy | sonnet | opus | Follow a hypothesis to depth before pivoting; synthesis ranks hypotheses |
| Design review | balanced | haiku | sonnet | Fast cheap variation + just enough consistency tracking |
| Looping | throughput | haiku | sonnet | Haiku/Haiku loses trajectory; Sonnet synthesis prevents circular repetition |

**Human-mode adjustment:** When you're in the loop, ACE drops the divergence model one tier and raises the interrupt budget. You provide creative pressure; AI amplifies and finds edge cases. This was the key post-debate insight: Opus-divergence competes with the human's contribution rather than supporting it.

**The synthesis-strength knob (1–5):** If a session feels too convergent (synthesis agreeing with everything), raise it. If it feels like synthesis can't keep up with the branches, lower it. Default: 4 for architecture, 3 for debugging, 2 for design-review, 1 for looping.

---

## Key concepts

**Attractor debt** — when the synthesis agent keeps deferring the same class of branch, debt accumulates as gravitational pull on the trajectory. When it exceeds the threshold, ACE surfaces those branches for mandatory re-examination. High debt = the trajectory is being warped by invisible pressure.

**Convergence warning** — if the synthesis agent agrees with everything AND the divergence budget is unused, the divergence agent may have been captured by the synthesis agent's frame. System failure, not success. Suppressed in human-mode (where you agreeing is healthy).

**Sophisticated echo** (from debate) — symmetric Opus/Opus coupling optimizes for agreement quality, not decision quality. Two Opus instances share the same prior distribution and miss risks they're both blind to. This is why synthesis-heavy beats symmetric for architecture.

**Relational context** — the coupling history between THIS specific session's agents. Not portable. Use `--state-file` to persist and inspect between sessions.
