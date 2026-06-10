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
    # ── Neuro-profile parameters (human-mode presets) ─────────────────────────
    # resonance_weight:          [0.0–1.0] weight of resonance signal in branch prioritization.
    #                            High for ADHD (interest-based nervous system);
    #                            moderate for monotropic/ASD (domain-governed motivation).
    # closure_pressure:          [0.0–1.0] how strongly the system nudges the human to close loops.
    #                            Low for ADHD (AI handles closure); higher for ASD
    #                            (monotropic users can spiral on precision indefinitely).
    # urgency_gate:              [0.0–1.0] urgency signal threshold to surface as prompt.
    #                            Low for ADHD (respond to urgency, catch drifts);
    #                            high for ASD (protect depth from false urgency).
    # depth_delta_floor_override: override for DEPTH_DELTA_FLOOR per preset.
    #                            None = use module constant (0.20).
    #                            Lower for ADHD (hyperfocus deepening may be compact).
    resonance_weight: float = 0.50
    closure_pressure: float = 0.50
    urgency_gate: float = 0.50
    depth_delta_floor_override: float | None = None
    # coherence_floor: [0.0–1.0] minimum branch coherence to survive into synthesis.
    #                  0.0 = off (novelty unconstrained — correct for Explorer/scattered work).
    #                  Raise for grounded/engineering topics where low-coherence "metaphor
    #                  soup" drowns actionable branches. Deep Focus sets 0.70.
    coherence_floor: float = 0.0


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
    #
    # The axis is ATTENTIONAL TOPOLOGY, not task domain:
    #   human-adhd:        broad-scan, high interrupt tolerance, DMN hyperactivity,
    #                      novelty-seeking, external closure support needed
    #   human-scientific:  narrow-channel sustained attention (monotropic/ASD-leaning),
    #                      precision premium, deep single-topic focus, switching is costly
    #
    # Note: human-creative is retained as a backward-compat alias for human-adhd.
    # Creative work is a task domain, not a cognitive profile. Creative work done
    # by an ADHD-profile user benefits from ADHD parameters; by a monotropic user,
    # from scientific parameters.

    "human-adhd": CouplingProfile(
        name="human-adhd",
        mode="human",
        divergence_model="claude-haiku-4-5-20251001",
        synthesis_model="claude-sonnet-4-6",
        synthesis_strength=3.0,       # high — ADHD users generate well, close poorly; AI takes closure
        base_interrupt_budget=8,      # high — short attention cycles; switching is natural
        debt_surface_threshold=2.0,   # low — surface fast before WM decay discards deferred items
        receptivity_noise_sigma=0.30, # high — affective lability; receptivity is volatile
        dynamic_cq=True,
        convergence_warning_enabled=False,  # ADHD diverges naturally; warning would desensitize
        human_divergence_model="claude-haiku-4-5-20251001",
        human_interrupt_budget=9,
        # Neuro-profile parameters
        resonance_weight=0.80,        # interest-based nervous system — resonance is the engagement lever
        closure_pressure=0.20,        # AI closes; don't pressure human mid-flow
        urgency_gate=0.40,            # moderate gate catches drifts without alarm fatigue
        depth_delta_floor_override=0.15,  # hyperfocus deepening may be compact but genuine
        description=(
            "Human thinking scaffold — ADHD-leaning attentional profile. "
            "Broad-scan mode: AI amplifies associative breadth, catches drift, provides closure. "
            "High interrupt budget (attention cycles are short); low debt threshold "
            "(surface before WM decay); high resonance weight (interest-based NS). "
            "Convergence warnings off — ADHD users diverge naturally. "
            "AI synthesis is integrative: stitches divergent threads the human won't close."
        ),
    ),
    "human-scientific": CouplingProfile(
        name="human-scientific",
        mode="human",
        divergence_model="claude-haiku-4-5-20251001",
        synthesis_model="claude-sonnet-4-6",
        synthesis_strength=1.5,       # low — precision user needs to see the seams; AI scaffolds minimally
        base_interrupt_budget=3,      # low — topic switches are expensive; protect deep work
        debt_surface_threshold=6.0,   # high — stable WM; can hold a large deferred queue
        receptivity_noise_sigma=0.10, # low — monotropic attention is stable within-topic
        dynamic_cq=True,
        convergence_warning_enabled=True,  # monotropic users can spiral on sub-problems
        human_divergence_model="claude-haiku-4-5-20251001",
        human_interrupt_budget=5,
        # Neuro-profile parameters
        resonance_weight=0.40,        # domain-governed motivation; resonance matters but is stable
        closure_pressure=0.65,        # gentle closure pressure — monotropic users spiral on precision
        urgency_gate=0.70,            # high — protect depth from false urgency
        depth_delta_floor_override=None,  # use default 0.20; monotropic deepening is verbose
        coherence_floor=0.70,         # grounded depth mode — reject low-coherence metaphor soup
        description=(
            "Human thinking scaffold — ASD/monotropic attentional profile. "
            "Narrow-channel depth mode: AI preserves precision, protects focus, "
            "warns on local minima (monotropic users can spiral on sub-problems). "
            "Low interrupt budget (switching is costly); high debt threshold "
            "(stable WM can hold a large deferred queue). "
            "AI synthesis is conservative: shows connections without collapsing distinctions."
        ),
    ),
    "human-creative": CouplingProfile(
        # Backward-compat alias for human-adhd.
        # Creative work is a task domain, not a cognitive profile.
        # Use human-adhd for creative tasks; use human-scientific for structured composition.
        name="human-creative",
        mode="human",
        divergence_model="claude-haiku-4-5-20251001",
        synthesis_model="claude-sonnet-4-6",
        synthesis_strength=3.0,
        base_interrupt_budget=8,
        debt_surface_threshold=2.0,
        receptivity_noise_sigma=0.30,
        dynamic_cq=True,
        convergence_warning_enabled=False,
        human_divergence_model="claude-haiku-4-5-20251001",
        human_interrupt_budget=9,
        resonance_weight=0.80,
        closure_pressure=0.20,
        urgency_gate=0.40,
        depth_delta_floor_override=0.15,
        description=(
            "Alias for human-adhd. Creative work is a task domain, not a cognitive profile. "
            "This preset is identical to human-adhd. For new sessions, prefer human-adhd "
            "or human-scientific based on your attentional profile, not task type."
        ),
    ),
}

DEFAULT_PRESET = "architecture"
DEFAULT_HUMAN_PRESET = "human-adhd"


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
    coherence_floor: float | None = None,
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
    if coherence_floor is not None:
        kwargs["coherence_floor"] = coherence_floor
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
