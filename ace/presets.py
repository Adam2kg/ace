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

from dataclasses import dataclass, field


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
    convergence_warning_enabled: bool = True
    description: str = ""
    # Root mode: what is being scaffolded?
    #   "ai"    — AI is doing the thinking; coupling reduces entropy toward resolution
    #             (Governor: minimize search space, follow hypothesis, synthesize hard)
    #   "human" — Human is doing the thinking; coupling produces entropy for reflection
    #             (Mirror: maximize search space, unstick attractors, synthesize gently)
    # These are anti-correlated optimization targets; coupling functions must not share state.
    mode: str = "ai"
    # Human-mode overrides: applied when --human-mode is active
    # When a human is in the loop they ARE the divergence engine;
    # AI divergence becomes an amplifier, not the primary generator.
    human_divergence_model: str = ""    # defaults to one tier below divergence_model
    human_interrupt_budget: int = 0     # defaults to base_interrupt_budget + 2
    # Frame mode: single-provider with cognitive frames instead of multi-provider dispatch.
    # Correct for: conceptual problems, budget ceiling, latency constraint, quota fallback,
    # data trust boundary, reproducibility, adversarial threat modeling.
    frames_only: bool = False
    frames_set: str = "general"         # "general" | "adversarial" — selects frame subset
    human_convergence_warning: bool = False  # high agreement is healthy in human-mode


PRESETS: dict[str, CouplingProfile] = {
    "architecture": CouplingProfile(
        name="architecture",
        divergence_model="claude-sonnet-4-6",
        synthesis_model="claude-opus-4-8",
        synthesis_strength=4.0,       # drops to 2.0 at session start if dynamic_cq=True
        base_interrupt_budget=4,
        debt_surface_threshold=2.5,
        receptivity_noise_sigma=0.2,
        dynamic_cq=True,
        human_divergence_model="claude-haiku-4-5-20251001",  # human IS the divergence engine
        human_interrupt_budget=6,     # human interrupts are the primary creative input
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
        debt_surface_threshold=3.0,   # surface debt late — follow a hypothesis to depth
        receptivity_noise_sigma=0.1,  # low noise — synthesis must be predictable
        dynamic_cq=False,
        human_divergence_model="claude-sonnet-4-6",  # no downgrade — fault-tree precision matters
        human_interrupt_budget=4,
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
        base_interrupt_budget=5,      # design review is iterative — more interrupts
        debt_surface_threshold=2.5,
        receptivity_noise_sigma=0.15,
        dynamic_cq=False,
        human_divergence_model="claude-haiku-4-5-20251001",  # already at minimum
        human_interrupt_budget=7,
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
        human_divergence_model="claude-haiku-4-5-20251001",  # no change
        human_interrupt_budget=3,
        description=(
            "Repetitive/looping work: Haiku divergence (variation-within-pattern) + "
            "Sonnet synthesis (enough state to avoid circular repetition). "
            "Haiku/Haiku would lose trajectory; Sonnet synthesis prevents that cheaply."
        ),
    ),
    "frames-deep": CouplingProfile(
        name="frames-deep",
        divergence_model="claude-sonnet-4-6",
        synthesis_model="claude-sonnet-4-6",
        synthesis_strength=3.0,
        base_interrupt_budget=5,
        debt_surface_threshold=2.0,
        receptivity_noise_sigma=0.15,
        dynamic_cq=False,
        frames_only=True,
        frames_set="general",
        description=(
            "Single-provider, multiple cognitive frames — no multi-provider dispatch. "
            "Correct when: conceptual/evaluative problem, budget < $0.10/query, "
            "latency < 2s, provider quota exhausted, or data cannot leave one trust boundary. "
            "Frame set: regulator, ten-year-old, inversion, remove-assumption, extreme-zero."
        ),
    ),
    "frames-adversarial": CouplingProfile(
        name="frames-adversarial",
        divergence_model="claude-sonnet-4-6",
        synthesis_model="claude-opus-4-8",
        synthesis_strength=4.0,
        base_interrupt_budget=4,
        debt_surface_threshold=2.5,
        receptivity_noise_sigma=0.1,
        dynamic_cq=False,
        frames_only=True,
        frames_set="adversarial",
        convergence_warning_enabled=False,  # adversarial frames produce intentional convergence
        description=(
            "Single-provider, adversarial frame set — for security threat modeling, "
            "regulated environments requiring reproducible outputs, and adversarial "
            "robustness testing. Consistent provider blind spots are preferable to "
            "variable cross-provider gaps when auditing attack surfaces. "
            "Frame set: adversary, inversion, ops-3am, extreme-zero, remove-assumption."
        ),
    ),
    # ── Human-mode presets ────────────────────────────────────────────────────
    # Mirror optimization: maximize entropy, unstick attractors, scaffold reflection.
    # AI divergence is an AMPLIFIER for human thinking, not the primary generator.
    # Synthesis is gentle — it surfaces and reflects, does not resolve and close.
    "human-scientific": CouplingProfile(
        name="human-scientific",
        mode="human",
        divergence_model="claude-haiku-4-5-20251001",
        synthesis_model="claude-sonnet-4-6",
        synthesis_strength=2.0,       # low — human drives, AI scaffolds
        base_interrupt_budget=6,      # high — human needs frequent prompts to unstick
        debt_surface_threshold=1.5,   # low — surface attractors aggressively (blockade mode)
        receptivity_noise_sigma=0.2,  # high — human thinking is unpredictable
        dynamic_cq=True,              # synthesis presence rises as session matures
        convergence_warning_enabled=True,  # warn on PREMATURE convergence (human locking up)
        human_divergence_model="claude-haiku-4-5-20251001",
        human_interrupt_budget=8,
        description=(
            "Human thinking scaffold — scientific/architectural domain. "
            "Primary signal: convergence rate toward falsifiable claims. "
            "Mirror mode: AI amplifies human divergence, surfaces attractor debt, "
            "warns when human locks onto a frame before testing it. "
            "Synthesis holds back at session start; presence rises as ideas accumulate."
        ),
    ),
    "human-creative": CouplingProfile(
        name="human-creative",
        mode="human",
        divergence_model="claude-haiku-4-5-20251001",
        synthesis_model="claude-sonnet-4-6",
        synthesis_strength=1.5,       # very low — creative work resists closure
        base_interrupt_budget=7,      # high — creative needs wide divergence window
        debt_surface_threshold=3.0,   # high — let attractor debt grow (productive discomfort)
        receptivity_noise_sigma=0.25, # highest — lateral leaps and serendipity required
        dynamic_cq=False,             # no automatic synthesis ramp — creative needs space
        convergence_warning_enabled=False,  # premature closure kills creative depth
        human_divergence_model="claude-haiku-4-5-20251001",
        human_interrupt_budget=9,
        description=(
            "Human thinking scaffold — creative/narrative domain. "
            "Primary signal: narrative tension gradient (surprise-to-coherence ratio). "
            "Mirror mode: AI maintains lateral association pressure, resists premature closure. "
            "Debt can grow large before synthesis — the human needs to live in "
            "productive discomfort. Convergence warnings suppressed: creative convergence "
            "is a choice, not a risk."
        ),
    ),
}

DEFAULT_PRESET = "architecture"
DEFAULT_HUMAN_PRESET = "human-scientific"


def get_preset(name: str) -> CouplingProfile:
    if name not in PRESETS:
        available = ", ".join(PRESETS.keys())
        raise ValueError(f"Unknown preset '{name}'. Available: {available}")
    return PRESETS[name]


def apply_human_mode(profile: CouplingProfile) -> CouplingProfile:
    """
    Adjust a preset for human-in-the-loop sessions.

    When the human is actively contributing divergence (ideas, pivots, framings),
    the AI divergence agent becomes an amplifier, not the primary generator.
    Convergence warnings are suppressed — high agreement is healthy in human-mode
    because the human IS the creative pressure.
    """
    from dataclasses import replace
    return replace(
        profile,
        divergence_model=profile.human_divergence_model or profile.divergence_model,
        base_interrupt_budget=profile.human_interrupt_budget or profile.base_interrupt_budget + 2,
        convergence_warning_enabled=False,
    )


def apply_overrides(
    profile: CouplingProfile,
    synthesis_strength: float | None = None,
    divergence_model: str | None = None,
    synthesis_model: str | None = None,
    budget: int | None = None,
    debt_threshold: float | None = None,
) -> CouplingProfile:
    """Apply explicit user overrides on top of a preset. Presets are defaults, not ceilings."""
    from dataclasses import replace
    kwargs: dict = {}
    if synthesis_strength is not None:
        kwargs["synthesis_strength"] = synthesis_strength
    if divergence_model is not None:
        kwargs["divergence_model"] = divergence_model
    if synthesis_model is not None:
        kwargs["synthesis_model"] = synthesis_model
    if budget is not None:
        kwargs["base_interrupt_budget"] = budget
    if debt_threshold is not None:
        kwargs["debt_surface_threshold"] = debt_threshold
    return replace(profile, **kwargs) if kwargs else profile


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
