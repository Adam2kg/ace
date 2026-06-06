# /ace — Asymmetric Cognitive Equilibrium

Run an ACE session: divergence agents (🔴🟡) generate branches in parallel,
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
          description: "AI providers (Codex, Gemini) generate the branches. Standard coupling dynamics."
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

| Human mode answer | CLI flag |
|------------------|----------|
| Yes | `--human-mode` |
| No | (omit) |

### Step 3 — Check providers and display banner

```bash
printf "codex:%s\n" "$(command -v codex >/dev/null 2>&1 && echo available || echo missing)"
printf "gemini:%s\n" "$(command -v gemini >/dev/null 2>&1 && echo available || echo missing)"
```

Display banner (MANDATORY before running):
```
🐙 ACE — Asymmetric Cognitive Equilibrium
Preset: [selected preset] [human-mode if active]
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
