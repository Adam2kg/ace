# ACE — Asymmetric Cognitive Equilibrium Engine

Multi-provider AI orchestration with a coupling function at the center.

Most multi-agent frameworks treat agents as workers with roles. ACE treats agents as **an environment for each other**. The divergence agent provides the instability that makes creativity available to the synthesis agent. The synthesis agent provides the stability that makes it safe for the divergence agent to generate extremes.

The coupling function — not the agents — is the primary design object.

---

## Architecture

```
Topic
  │
  ├─── 🔴 Codex ────────────────────────────────┐
  │    (divergence: technical branches)          │
  │                                              ▼
  ├─── 🟡 Gemini ───────────────────────► COUPLING FUNCTION
  │    (divergence: lateral branches)            │
  │                                    ┌─────────┴──────────┐
  │                                    │  interrupt_budget   │
  │                                    │  receptivity_signal │
  │                                    │  deferral_queue     │
  │                                    │  attractor_debt     │
  │                                    │  relational_context │
  │                                    └─────────┬──────────┘
  │                                              │
  └─── 🔵 Claude ◄───── synthesis ◄─────────────┘
       (trajectory maintenance)
              │
              ▼
       Trajectory Update + Coupling State
```

### The Coupling Function governs four primitives

| Primitive | Description |
|-----------|-------------|
| `interrupt_budget` | How many divergence interrupts per synthesis cycle. Replenishes as synthesis produces trajectory segments — load-sensitive, no explicit negotiation. |
| `receptivity_signal` | Synthesis signals OPEN / NEUTRAL / CONSOLIDATING / LOCKED. Includes a noise term so the divergence agent can never perfectly predict acceptance — prevents creative range collapse. |
| `deferral_queue` | Branches not yet integrated. Each deferral increments exponentially-weighted **attractor debt** — the gravitational pull of consistently-avoided states. |
| `handoff_state` | Full state at phase transitions, including `relational_context` — the memory that cannot survive re-pairing with a different agent. |

---

## Key Properties

**The stabilizer is a compression function, not a filter.** It assigns *trajectory weight*, not yes/no. The same idea means something different depending on when it arrives.

**The divergence agent's errors are load-bearing.** If you optimize the divergence agent to be more "on-topic," you degrade the system. The tangents are the entropy injection that prevents local-minimum convergence.

**High agreement between agents is a warning signal.** If the synthesis agent integrates everything and the divergence budget is unused, the divergence agent has been captured — system failure, not success.

**Attractor debt surfaces invisible gravitational forces.** Deferred branches accumulate weight. When debt crosses the threshold, ACE surfaces them for mandatory re-examination before the trajectory can continue.

**Relational context is not portable.** Some memory exists only in the coupling history between *this specific pair* of agents. Archiving either agent individually loses it.

---

## Install

```bash
pip install -e .
```

Requires: Python ≥ 3.11, `codex` CLI (OpenAI), `gemini` CLI (Google), `claude` CLI (Anthropic).

---

## Usage

```bash
# Single diverge→synthesize cycle
ace run "how should we architect the auth service"

# Three cycles — trajectory evolves across rounds
ace run "redesign the data pipeline" --cycles 3

# Persist coupling state for debt inspection
ace run "choose between GraphQL and REST" --state-file session.json

# Inspect attractor debt from saved state
ace debt --state-file session.json

# Use specific providers
ace run "optimize the cold path" --providers codex,gemini
```

---

## Mapping to Octopus providers

| ACE Role | Octopus Provider | Indicator |
|----------|-----------------|-----------|
| Divergence (technical) | Codex CLI | 🔴 |
| Divergence (lateral) | Gemini CLI | 🟡 |
| Synthesis | Claude (via `claude` CLI) | 🔵 |

The Octopus bridge skill (`skills/ace.md`) makes ACE invokable as `/ace <topic>` from Claude Code.

---

## Extending

The coupling function is designed to be the unit of experimentation:

```python
from ace.coupling.function import CouplingFunction

# Tighter creative pressure
coupling = CouplingFunction(
    base_interrupt_budget=5,
    receptivity_noise_sigma=0.3,   # higher noise = less predictable synthesis
    debt_surface_threshold=1.5,    # surface attractor debt sooner
)
```

Wire to your own agents via `ace.agents.divergence.diverge()` and `ace.agents.synthesis.synthesize()`, or replace them entirely — the coupling function is independent.

---

## Why this is different from CrewAI / AutoGen / LangGraph

Those frameworks design agents and then decide how they communicate.

ACE designs the communication protocol first. Two mediocre agents with a well-designed coupling function will outperform two excellent agents with a naive one.

The coupling function in ACE is:
- **Observable** — real-time budget, debt, convergence warnings
- **Separately tunable** from either agent
- **The unit of experimentation** — vary coupling, hold agents constant

---

## Concepts coined in the design session

**Attractor debt** — the gravitational field built up by consistently-deferred branches. Not the same as memory. Decays with time but compounds with repeat deferral.

**Creative phase-locking** — when both agents' cadences synchronize, output quality drops. Good output requires productive asynchrony.

**Co-regulated memory** — memory encoded in the coupling history between a specific pair. Non-portable. The most important information the system generates that no agent individually holds.

**Regulatory lag as signal** — synthesis response latency tells you about trajectory confidence, not just performance. Short lag = uncertainty, monitoring closely. Long lag = trajectory is stable.

---

*Inspired by complementary neurodiverse interaction patterns as a design frame for cooperative cognitive architectures.*
