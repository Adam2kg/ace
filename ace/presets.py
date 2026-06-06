"""
Task-type coupling presets for ACE.

Derived from a 3-round multi-provider debate on model strength asymmetry.
Key findings:
  - Model strength is a first-class coupling parameter (not orthogonal)
  - Synthesis holds trajectory across cycles → synthesis earns the stronger model first
  - A weaker synthesis agent defers from INCAPACITY, not judgment — the coupling function
    cannot distinguish these, so convergence warnings fire for the wrong reason
  - Synthesis strength should drop at session START (divergence-first) and rise as
    the session matures (consolidation-dominant) — dynamic CQ across phases

Architecture preset:
  - Synthesis-heavy (Sonnet divergence + Opus synthesis)
  - Rationale: architecture already has a divergence engine (the human); AI synthesis
    depth is what's missing. Opus-divergence competes with the human, not supports them.

Debugging preset:
  - Symmetric Sonnet; synthesis slightly stronger
  - Fault-tree branches need precision, not creativity; synthesis must rank hypotheses

Looping/repetitive preset:
  - Haiku divergence + Sonnet synthesis (not Haiku/Haiku)
  - Sonnet synthesis keeps enough trajectory state to avoid circular repetition
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CouplingProfile:
    """Full coupling configuration for a task type."""
    name: str
    divergence_model: str       # e.g. "claude-haiku-4-5", "claude-sonnet-4-6"
    synthesis_model: str        # e.g. "claude-sonnet-4-6", "claude-opus-4-8"
    synthesis_strength: float   # 1.0–5.0; user-visible knob
    base_interrupt_budget: int
    debt_surface_threshold: float
    receptivity_noise_sigma: float
    dynamic_cq: bool            # if True, synthesis_strength rises as session matures
    description: str = ""


PRESETS: dict[str, CouplingProfile] = {
    "architecture": CouplingProfile(
        name="architecture",
        divergence_model="claude-sonnet-4-6",
        synthesis_model="claude-opus-4-8",
        synthesis_strength=4.0,     # drops to 2.0 at session start if dynamic_cq=True
        base_interrupt_budget=4,
        debt_surface_threshold=2.5,
        receptivity_noise_sigma=0.2,
        dynamic_cq=True,
        description=(
            "Architecture: synthesis-heavy. Human provides divergence; AI provides "
            "trajectory depth. Opus synthesis integrates contradictory constraints "
            "across long context without losing load-bearing nuance."
        ),
    ),
    "debugging": CouplingProfile(
        name="debugging",
        divergence_model="claude-sonnet-4-6",
        synthesis_model="claude-opus-4-8",
        synthesis_strength=3.0,
        base_interrupt_budget=3,
        debt_surface_threshold=3.0,   # surface debt late — debugging needs sustained trajectory
        receptivity_noise_sigma=0.1,  # low noise — synthesis must be predictable
        dynamic_cq=False,
        description=(
            "Debugging: precise fault-tree divergence (Sonnet), strong causal-chain "
            "integration (Opus). Low noise: debugging needs consistent synthesis. "
            "Higher debt threshold: follow a hypothesis to depth before pivoting."
        ),
    ),
    "design-review": CouplingProfile(
        name="design-review",
        divergence_model="claude-haiku-4-5-20251001",
        synthesis_model="claude-sonnet-4-6",
        synthesis_strength=2.0,
        base_interrupt_budget=5,      # more interrupts — design review is iterative
        debt_surface_threshold=2.5,
        receptivity_noise_sigma=0.15,
        dynamic_cq=False,
        description=(
            "Design review: cheap fast divergence (Haiku) generates variation; "
            "Sonnet synthesis tracks consistency. Synthesis stronger than divergence "
            "to catch pattern violations across many small changes."
        ),
    ),
    "looping": CouplingProfile(
        name="looping",
        divergence_model="claude-haiku-4-5-20251001",
        synthesis_model="claude-sonnet-4-6",
        synthesis_strength=1.0,
        base_interrupt_budget=2,
        debt_surface_threshold=5.0,   # don't surface debt — looping has no trajectory to protect
        receptivity_noise_sigma=0.05, # near-deterministic — throughput over creativity
        dynamic_cq=False,
        description=(
            "Repetitive/looping work: Haiku divergence (variation-within-pattern) + "
            "Sonnet synthesis (enough state to avoid circular repetition). "
            "Haiku/Haiku would lose trajectory; Sonnet synthesis prevents that cheaply."
        ),
    ),
}

DEFAULT_PRESET = "architecture"


def get_preset(name: str) -> CouplingProfile:
    if name not in PRESETS:
        available = ", ".join(PRESETS.keys())
        raise ValueError(f"Unknown preset '{name}'. Available: {available}")
    return PRESETS[name]


def effective_synthesis_strength(
    profile: CouplingProfile,
    session_cycle: int,
    total_cycles: int,
) -> float:
    """
    When dynamic_cq=True, synthesis strength rises as the session matures.
    Early exploration = divergence-first (lower CQ).
    Late consolidation = synthesis-dominant (higher CQ).
    """
    if not profile.dynamic_cq or total_cycles <= 1:
        return profile.synthesis_strength
    progress = session_cycle / total_cycles  # 0.0 → 1.0
    early_strength = max(1.0, profile.synthesis_strength - 2.0)
    return early_strength + (profile.synthesis_strength - early_strength) * progress
