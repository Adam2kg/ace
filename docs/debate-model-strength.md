# Debate: Model Strength Assignment in ACE

**Topic:** Does asymmetry between divergence (ADHD-mode) and synthesis (Autism-mode) model strength change coupling dynamics, or only output quality?

**Format:** 3 rounds, 3 participants (Gemini CLI, Claude Sonnet subagent, Claude moderator). Codex hit quota all rounds.

**Focus:** Coupling dynamics (not output quality, not budget optimization).

---

## Verdict

**Model strength is a first-class coupling parameter.** All three participants agreed. The mechanisms they named:

- A capacity-limited synthesis agent defers from **incapacity**, not judgment. The coupling function cannot distinguish these causes. Convergence warnings fire for the wrong diagnostic reason.
- Attractor debt accumulates faster under a weaker synthesis agent — not from creative pressure but from integration bandwidth limits. The trajectory shape changes, not just quality.
- High-frequency low-signal deferrals (Haiku) vs. low-frequency high-signal deferrals (Opus) are categorically different distributions. The coupling function sees the same token but the base rates are orders of magnitude apart.

**Architecture preset winner: synthesis-heavy** (Sonnet-divergence + Opus-synthesis). 2-1 over symmetric Opus/Opus.

---

## Key Concepts Coined

**Sophisticated echo** (Sonnet) — symmetric Opus/Opus coupling optimizes for agreement quality, not decision quality. Two Opus instances share the same prior distribution and converge on locally coherent answers that miss risks they're both blind to.

**Coupling Quotient / CQ** (Gemini) — Synthesis Fidelity / Divergence Entropy. CQ ≈ 1 = coherent evolution. CQ < 1 = amnesic drift. Architecture is not tolerant of CQ < 1 at any phase.

**Architectural amnesia** (Gemini) — Haiku synthesis doesn't accumulate attractor debt; it *defaults on it*. It lacks semantic gravity to hold Opus-level divergence, so the system forgets why a path was abandoned.

**Politely documenting your inadequacy** (Sonnet) — what the "controlled spiral" (Opus-diverge + Haiku-synthesize + low debt threshold) actually does. A tight threshold makes Haiku flag more often. It still can't perform the synthesis it flags for.

**Phase control** (Sonnet) — synthesis strength is not a fixed preset parameter; it is a phase control. Drop to lower strength in early exploration (divergence-first). Rise to higher strength in closing consolidation (synthesis-dominant). This is what `dynamic_cq=True` implements in `presets.py`.

---

## Final Preset Table

| Task | Divergence | Synthesis | Synthesis Strength | CQ Behavior |
|------|-----------|-----------|-------------------|-------------|
| Architecture | sonnet | opus | 4/5 (dynamic) | Rises from 2→4 across session |
| Debugging | sonnet | opus | 3/5 | Fixed — follow hypothesis to depth |
| Design review | haiku | sonnet | 2/5 | Fixed |
| Looping | haiku | sonnet | 1/5 | Fixed — throughput mode |

---

## The Human Factor (Post-Debate Insight)

**Architecture already has a divergence engine: the human.** When a person is actively in the loop providing ideas, pivots, and framing shifts, the AI divergence agent's role shifts from *primary generator* to *amplifier and edge-case finder*. Opus-divergence in that context competes with the human's creative contribution rather than supporting it.

This implies a **human-mode adjustment** for each preset:

- Architecture (human-in-loop): drop divergence from Sonnet → Haiku. Increase `base_interrupt_budget` (human interrupts are now the primary creative input; AI interrupts should amplify, not override).
- Debugging (human-in-loop): the human provides the reproduction case and initial hypothesis. AI divergence generates alternative fault trees. Sonnet divergence still correct — precision matters here.
- Design review (human-in-loop): Haiku divergence is already cheap enough. No change.

The human factor also changes how we interpret **convergence warnings**. If the human is driving divergence and the synthesis agent is integrating most of what comes in, high agreement rate is expected and healthy — the human IS the coupling function's creative pressure. The convergence warning threshold should be disabled or raised significantly in human-mode.

---

## What the Preset System Must Expose

1. **`--preset <name>`** — select coupling profile
2. **`--synthesis-strength <1-5>`** — override the ratio without knowing the model names
3. **`--human-mode`** — shift divergence down one tier; disable convergence warnings; increase interrupt budget for human-side creativity
4. **`--divergence-model <model>`** — direct override for power users
5. **`--synthesis-model <model>`** — direct override for power users

Presets are defaults. Every parameter is overridable. The preset system should never be the ceiling.

---

## Open Questions

1. Can the coupling function auto-detect task type from content (topic keywords, question structure) and suggest a preset? Or does requiring explicit selection keep the system more honest about what it's doing?
2. Should `dynamic_cq` be the default for ALL presets, not just architecture?
3. The "synthesis strength knob" (1-5) — what is its mapping to actual coupling parameters? Linear interpolation across `debt_surface_threshold`, `receptivity_noise_sigma`, and `interrupt_budget`?
