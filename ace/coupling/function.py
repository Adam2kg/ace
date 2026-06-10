"""
The coupling function is the primary design object in ACE.

Two agents — divergence (ADHD-mode) and synthesis (Autism-mode) — are secondary.
The protocol governing when they interact, how state transfers, and what gets deferred
determines whether the pair produces non-obvious coherent output or just noise.

Design axioms:
  1. The coupling function is more important than either agent.
  2. It must be fully observable in real-time.
  3. It is the unit of experimentation — vary coupling, hold agents constant.
  4. High agreement between agents is a warning signal, not a success metric.
"""

from __future__ import annotations

import math
import random
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ReceptivityState(Enum):
    OPEN = "open"            # actively soliciting divergence
    NEUTRAL = "neutral"      # standard operating
    CONSOLIDATING = "consolidating"  # mid-synthesis, budget frozen
    LOCKED = "locked"        # trajectory committed


# ── Depth / circularity detection thresholds ─────────────────────────────────
# All module-level so they can be monkey-patched in tests.

CIRCULAR_VISIT_THRESHOLD: int = 3    # visits needed before warning can fire
CIRCULAR_DELTA_FLOOR: float = 0.08   # progress delta below this = circular
DEPTH_DELTA_FLOOR: float = 0.20      # progress delta above this = deepening (monotropic flow)
DEPTH_VISIT_THRESHOLD: int = 2       # consecutive deepening visits to promote depth signal
CHRONIC_BRANCH_COUNT: int = 2        # circular branches needed to fire overthinking_warning

# Stopwords for keyword extraction — expand as needed per domain.
_ACE_STOPWORDS: frozenset[str] = frozenset({
    "that", "this", "with", "from", "have", "been", "will", "they",
    "what", "when", "then", "than", "also", "into", "some", "more",
    "about", "which", "there", "their", "were", "just", "very",
    "would", "could", "should", "does", "like", "each", "only",
})


@dataclass
class ScoreVector:
    """
    Metadata from the divergence scoring pass (populated by adhd-style scoring).
    Used by the coupling function as weights, never as prune gates.

    novelty:          0-1, semantic distance from the current working frame.
                      0.0 = fully redundant, 1.0 = maximally foreign.
    coherence:        0-1, internal logical consistency of the branch.
    frame_saturation: 0-1, how much of the current frame's vocabulary this branch covers.
                      High saturation → frame drift risk in multi-round sessions.
    resonance:        0-1, cross-branch echoing. How strongly this branch rhymes with
                      sibling branches already in play. 0.0 = isolated idea,
                      1.0 = maximally echoed across the active branch set.
    depth_pressure:   0-1, accumulated elaboration demand. Concepts introduced relative
                      to current expansion level — proxy for unresolved complexity.
    """
    novelty: float = 0.5
    coherence: float = 0.5
    frame_saturation: float = 0.0
    resonance: float = 0.0       # NEW: cross-branch amplification signal
    depth_pressure: float = 0.0  # NEW: unresolved elaboration demand


# Sentinel for unscored branches. All values are neutral (0.5 for normalized fields,
# 0.0 for additive fields). An unscored branch receives neutral synthesis weight —
# neither promoted nor suppressed. Use branch.effective_score everywhere.
SCORE_UNINITIALISED = ScoreVector(
    novelty=0.5,
    coherence=0.5,
    frame_saturation=0.0,
    resonance=0.0,
    depth_pressure=0.0,
)


@dataclass
class VisitSnapshot:
    """
    Immutable record of a branch's state at a single defer() or integrate() call.
    Capped at 10 per branch to bound memory.
    """
    timestamp: float
    content_length: int
    keyword_set: frozenset[str]
    visit_type: str       # "defer" | "integrate"
    delta_score: float    # _branch_progress_delta() result; 0.0 for first visit


@dataclass
class DepthAttractorSignal:
    """
    Positive signal: a branch is deepening (monotropic flow), not looping.
    Stored on CouplingFunction. Cleared when the branch is integrated.
    When a branch keeps returning AND shows progress, that is the strength to amplify.
    """
    branch_sig: str               # branch.content[:80]
    promoted_at: float            # epoch seconds
    visit_count: int              # visit count at time of promotion
    peak_delta: float             # highest delta_score seen across all visits
    keyword_trajectory: list[frozenset[str]]  # keyword sets across visits, for display


@dataclass
class Branch:
    content: str
    timestamp: float = field(default_factory=time.time)
    trajectory_context: dict[str, Any] = field(default_factory=dict)
    receptivity_at_deferral: ReceptivityState = ReceptivityState.NEUTRAL
    deferred_count: int = 0
    decay_constant: float = 0.1   # higher = faster decay of debt weight
    # Frame and scoring fields — optional, all backward-compatible
    frame_id: str | None = None        # which cognitive frame generated this branch
    score: ScoreVector | None = None   # populated by adhd-style scoring pass
    low_trust_flag: bool = False        # True when coherence < 0.3; propagates to synthesis
    # Visit history for depth/circularity detection (capped at 10 entries)
    visit_history: list[VisitSnapshot] = field(default_factory=list)
    depth_promotions: int = 0     # how many times this branch triggered depth_attractor_signal

    @property
    def effective_score(self) -> ScoreVector:
        """
        Always use this in synthesis weight formulas.
        Returns score if set, or SCORE_UNINITIALISED sentinel.
        Avoids scattered None-guards throughout the codebase.
        """
        return self.score if self.score is not None else SCORE_UNINITIALISED


@dataclass
class RelationalContext:
    """
    The memory that cannot be ported to a new co-regulation partner.
    Encoded in coupling history, not in either agent.
    """
    accepted_signatures: list[str] = field(default_factory=list)
    deferred_signatures: list[str] = field(default_factory=list)
    interrupt_response_times: list[float] = field(default_factory=list)
    phase: str = "divergent"

    def avg_response_time(self) -> float:
        if not self.interrupt_response_times:
            return 0.0
        return sum(self.interrupt_response_times) / len(self.interrupt_response_times)


class CouplingFunction:
    """
    The protocol between divergence and synthesis agents.

    Governs:
      - interrupt_budget: how many divergence interrupts per synthesis cycle
      - receptivity_signal: synthesis side's open/neutral/consolidating/locked state
      - deferral_queue: branches not yet integrated, accumulating attractor debt
      - handoff_protocol: state transferred between agents at phase transitions
    """

    def __init__(
        self,
        base_interrupt_budget: int = 3,
        budget_per_trajectory_segment: int = 1,
        receptivity_noise_sigma: float = 0.15,
        debt_surface_threshold: float = 2.5,
        mode: str = "ai",
    ):
        self.base_interrupt_budget = base_interrupt_budget
        self.budget_per_segment = budget_per_trajectory_segment
        self.receptivity_noise_sigma = receptivity_noise_sigma
        self.debt_surface_threshold = debt_surface_threshold
        # Root mode: "ai" (Governor — entropy reduction) or "human" (Mirror — entropy production).
        # These are anti-correlated optimization targets; do NOT share a CouplingFunction
        # instance across modes in the same session.
        self.mode = mode

        self._interrupt_budget = base_interrupt_budget
        # Human-mode starts OPEN: the human needs the widest divergence window immediately.
        # AI-mode starts NEUTRAL: synthesis pressure builds from a stable baseline.
        self._receptivity = ReceptivityState.OPEN if mode == "human" else ReceptivityState.NEUTRAL
        self._deferral_queue: list[Branch] = []
        self._trajectory_segments_completed = 0
        self._cycle_start = time.time()
        self._mode_transitions: list[dict] = []   # explicit named mode switches within session
        self.relational_context = RelationalContext()
        # Positive depth signals: branches in monotropic flow (deepening, not looping).
        # These are cleared when the branch integrates.
        self.depth_attractor_signals: list[DepthAttractorSignal] = []

    # ── Interrupt budget ─────────────────────────────────────────────────────

    def can_interrupt(self, emergency: bool = False) -> bool:
        cost = 2 if emergency else 1
        return self._interrupt_budget >= cost

    def consume_interrupt(self, emergency: bool = False) -> bool:
        cost = 2 if emergency else 1
        if self._interrupt_budget < cost:
            return False
        self._interrupt_budget -= cost
        return True

    def on_trajectory_segment_complete(self) -> None:
        """Synthesis signals a segment done — replenishes interrupt budget."""
        self._trajectory_segments_completed += 1
        self._interrupt_budget = min(
            self._interrupt_budget + self.budget_per_segment,
            self.base_interrupt_budget * 2,  # cap at 2x base
        )
        t = time.time() - self._cycle_start
        self.relational_context.interrupt_response_times.append(t)
        self._cycle_start = time.time()

    # ── Receptivity signaling ─────────────────────────────────────────────────

    def set_receptivity(self, state: ReceptivityState) -> None:
        self._receptivity = state
        if state == ReceptivityState.OPEN:
            self._interrupt_budget += 2

    def effective_receptivity(self) -> ReceptivityState:
        """
        Add a small noise term so the divergence agent can never perfectly
        predict the synthesis agent's state. Prevents the ADHD agent from
        learning to only send ideas when guaranteed acceptance — which would
        collapse the creative range over time.
        """
        noise = random.gauss(0, self.receptivity_noise_sigma)
        states = list(ReceptivityState)
        current_idx = states.index(self._receptivity)
        noisy_idx = max(0, min(len(states) - 1, round(current_idx + noise)))
        return states[noisy_idx]

    # ── Deferral and attractor debt ───────────────────────────────────────────

    def defer(self, branch: Branch) -> None:
        """Defer a branch; records a visit snapshot for depth/circularity tracking."""
        branch.deferred_count += 1
        branch.receptivity_at_deferral = self._receptivity
        branch.trajectory_context = self._snapshot_trajectory()

        # Record visit snapshot BEFORE appending to queue
        delta = self._branch_progress_delta(branch)
        snapshot = VisitSnapshot(
            timestamp=time.time(),
            content_length=len(branch.content),
            keyword_set=self._extract_keywords(branch.content),
            visit_type="defer",
            delta_score=delta,
        )
        # Cap history at 10 entries
        if len(branch.visit_history) >= 10:
            branch.visit_history.pop(0)
        branch.visit_history.append(snapshot)

        self._deferral_queue.append(branch)

    def integrate(self, branch: Branch) -> None:
        """Mark a branch as accepted into the trajectory."""
        # Archival snapshot — terminal, not used in delta calculations
        snapshot = VisitSnapshot(
            timestamp=time.time(),
            content_length=len(branch.content),
            keyword_set=self._extract_keywords(branch.content),
            visit_type="integrate",
            delta_score=0.0,
        )
        branch.visit_history.append(snapshot)

        # Clear depth signals for this branch (it has been resolved)
        self.clear_depth_signals(branch.content[:80])

        self._deferral_queue = [b for b in self._deferral_queue if b is not branch]
        sig = branch.content[:80]
        self.relational_context.accepted_signatures.append(sig)

    def attractor_debt(self) -> dict[str, float]:
        """
        Debt score per branch = Σ exp(-λ * age) * deferred_count.
        High debt = strong gravitational pull toward that branch class.
        When debt exceeds threshold, the synthesis agent should surface it.
        """
        now = time.time()
        debts = {}
        for b in self._deferral_queue:
            age = now - b.timestamp
            weight = math.exp(-b.decay_constant * age) * b.deferred_count
            sig = b.content[:40]
            debts[sig] = debts.get(sig, 0) + weight
        return dict(sorted(debts.items(), key=lambda x: x[1], reverse=True))

    def high_debt_branches(self) -> list[Branch]:
        now = time.time()
        result = []
        for b in self._deferral_queue:
            age = now - b.timestamp
            debt = math.exp(-b.decay_constant * age) * b.deferred_count
            if debt >= self.debt_surface_threshold:
                result.append(b)
        return result

    # ── Handoff protocol ──────────────────────────────────────────────────────

    def handoff_state(self) -> dict[str, Any]:
        """
        Everything required for a phase transition between agents.
        This is the state that cannot survive re-pairing with a different agent.
        """
        return {
            "mode": self.mode,
            "mode_transitions": self._mode_transitions,
            "interrupt_budget": self._interrupt_budget,
            "receptivity": self._receptivity.value,
            "deferred_count": len(self._deferral_queue),
            "trajectory_segments_completed": self._trajectory_segments_completed,
            "attractor_debt": self.attractor_debt(),
            "high_debt_branches": [b.content for b in self.high_debt_branches()],
            "depth_attractors": [
                {"sig": s.branch_sig, "visit_count": s.visit_count, "peak_delta": s.peak_delta}
                for s in self.depth_attractor_signals
            ],
            "relational_context": {
                "avg_response_time": self.relational_context.avg_response_time(),
                "accepted_count": len(self.relational_context.accepted_signatures),
                "deferred_count": len(self.relational_context.deferred_signatures),
                "phase": self.relational_context.phase,
            },
        }

    # ── Keyword extraction ────────────────────────────────────────────────────

    @staticmethod
    def _extract_keywords(text: str) -> frozenset[str]:
        """
        Stopword-filtered, lowercase, alpha-only tokens, length >= 4.
        No stemming. No models. Pure heuristic.
        """
        tokens = re.findall(r'[a-z]{4,}', text.lower())
        return frozenset(t for t in tokens if t not in _ACE_STOPWORDS)

    # ── Depth / circularity detection ─────────────────────────────────────────

    def _branch_progress_delta(self, branch: Branch) -> float:
        """
        Return [0.0, 1.0] measuring how much the branch has progressed since last visit.
        0.0 = circular (same content, same words, same structure).
        1.0 = maximum progress.

        Three equal-weight signals:
          CLDelta: content length change (deepening adds words)
          KNDelta: keyword Jaccard complement (deepening introduces new vocabulary)
          SNDelta: sentence count delta (deepening adds propositions)
        """
        if not branch.visit_history:
            return 0.0  # first visit — no prior to compare

        prior = branch.visit_history[-1]
        current_length = len(branch.content)
        current_kw = self._extract_keywords(branch.content)

        # Signal A: content length delta
        cl_delta = min(abs(current_length - prior.content_length) / max(prior.content_length, 1), 1.0)

        # Signal B: keyword Jaccard complement (new vocabulary fraction)
        union = prior.keyword_set | current_kw
        kn_delta = len(current_kw - prior.keyword_set) / len(union) if union else 0.0

        # Signal C: sentence count delta (80-char estimate per sentence)
        prior_sentences = max(1, prior.content_length // 80)
        current_sentences = max(1, current_length // 80)
        sn_delta = min(max((current_sentences - prior_sentences) / prior_sentences, 0.0), 1.0)

        return (cl_delta + kn_delta + sn_delta) / 3.0

    def _is_deepening(self, branch: Branch) -> bool:
        """
        True if the last DEPTH_VISIT_THRESHOLD visits all show genuine progress.
        Monotropic flow: same attractor, consistently advancing.
        """
        if len(branch.visit_history) < DEPTH_VISIT_THRESHOLD:
            return False
        recent = branch.visit_history[-DEPTH_VISIT_THRESHOLD:]
        return all(v.delta_score >= DEPTH_DELTA_FLOOR for v in recent)

    def _promote_depth_attractor(self, branch: Branch) -> None:
        """
        Promote a deepening branch to the depth_attractor_signals list.
        Idempotent: will not re-promote the same branch within the same cycle.
        """
        sig = branch.content[:80]
        if any(s.branch_sig == sig for s in self.depth_attractor_signals):
            return

        signal = DepthAttractorSignal(
            branch_sig=sig,
            promoted_at=time.time(),
            visit_count=len(branch.visit_history),
            peak_delta=max((v.delta_score for v in branch.visit_history), default=0.0),
            keyword_trajectory=[v.keyword_set for v in branch.visit_history],
        )
        self.depth_attractor_signals.append(signal)
        branch.depth_promotions += 1

    def clear_depth_signals(self, branch_sig: str | None = None) -> None:
        """
        Clear depth attractor signals for a specific branch (by content[:80] sig),
        or clear all signals if branch_sig is None.
        Called automatically at integrate() time.
        """
        if branch_sig is None:
            self.depth_attractor_signals.clear()
        else:
            self.depth_attractor_signals = [
                s for s in self.depth_attractor_signals if s.branch_sig != branch_sig
            ]

    # ── Synthesis weight formulas ─────────────────────────────────────────────

    def synthesis_weight_mirror(self, branch: Branch) -> float:
        """
        MIRROR mode (ADHD-leaning) synthesis weight.

        Rewards novelty + resonance. Novelty is the primary driver (escape vectors are
        valuable; high-novelty/low-resonance branches are cognitive escape vectors that
        haven't rhymed with anything yet because nothing like them exists).
        Coherence is a soft floor at 0.3, not a gate — loose coherence is expected
        in divergent mode. depth_pressure is intentionally absent (unresolved threads
        ARE the expected shape of ADHD-mode working space).

        Formula:
            0.45 * novelty
          + 0.30 * resonance
          + 0.15 * sigmoid(coherence, threshold=0.3, slope=8)
          - 0.10 * frame_saturation
        """
        s = branch.effective_score
        coherence_floor = 1.0 / (1.0 + math.exp(-8.0 * (s.coherence - 0.3)))
        weight = (
            0.45 * s.novelty
            + 0.30 * s.resonance
            + 0.15 * coherence_floor
            - 0.10 * s.frame_saturation
        )
        return max(0.0, weight)

    def synthesis_weight_governor(self, branch: Branch) -> float:
        """
        GOVERNOR mode (ASD/monotropic-leaning) synthesis weight.

        Coherence is primary (hard gate at 0.6). Novelty is gated by resonance:
        novelty alone without echoing context is noise; novelty that rhymes with
        existing work is valuable. Systematic frame coverage is rewarded.
        depth_pressure is penalized — unresolved elaboration is cognitive overhead
        in a precision-oriented mode.

        Formula:
            0.40 * sigmoid(coherence, threshold=0.6, slope=12)
          + 0.25 * (novelty * resonance)      ← product enforces both nonzero
          + 0.15 * frame_saturation
          - 0.20 * depth_pressure
        """
        s = branch.effective_score
        coherence_gate = 1.0 / (1.0 + math.exp(-12.0 * (s.coherence - 0.6)))
        resonance_gated_novelty = s.novelty * s.resonance
        weight = (
            0.40 * coherence_gate
            + 0.25 * resonance_gated_novelty
            + 0.15 * s.frame_saturation
            - 0.20 * s.depth_pressure
        )
        return max(0.0, weight)

    def synthesis_weight(self, branch: Branch) -> float:
        """
        Backward-compatible alias for synthesis_weight_mirror().
        Existing callsites (frame_monoculture_risk, etc.) continue to work unchanged.
        """
        return self.synthesis_weight_mirror(branch)

    def frame_monoculture_risk(self, branches: list[Branch]) -> bool:
        """
        True when > 80% of weighted branches share the same frame_id.
        Signals diversity failure: all divergence came from one cognitive angle.
        Caller should rotate frames rather than continuing.
        """
        scored = [b for b in branches if b.score is not None and b.frame_id is not None]
        if len(scored) < 2:
            return False
        weights = [(b, self.synthesis_weight(b)) for b in scored]
        total = sum(w for _, w in weights)
        if total == 0.0:
            return False
        frame_share: dict[str, float] = {}
        for b, w in weights:
            fid = b.frame_id or "unknown"
            frame_share[fid] = frame_share.get(fid, 0.0) + w
        return max(frame_share.values()) / total > 0.8

    # ── Mode transition ───────────────────────────────────────────────────────

    def transition_mode(self, new_mode: str, reason: str = "") -> None:
        """
        Explicitly switch the coupling function's optimization target mid-session.
        This is a named event — it is tracked in the session record, not silent.
        The caller is responsible for instantiating a new CouplingFunction for the
        new mode if strict isolation is required; this method records the transition.
        """
        self._mode_transitions.append({
            "from": self.mode,
            "to": new_mode,
            "reason": reason,
            "at_segment": self._trajectory_segments_completed,
            "timestamp": time.time(),
        })
        old_mode = self.mode
        self.mode = new_mode
        if new_mode == "human" and old_mode == "ai":
            self._receptivity = ReceptivityState.OPEN
            self._interrupt_budget = max(self._interrupt_budget, self.base_interrupt_budget)
        elif new_mode == "ai" and old_mode == "human":
            if self._receptivity == ReceptivityState.OPEN:
                self._receptivity = ReceptivityState.NEUTRAL

    # ── Convergence and overthinking detection ────────────────────────────────

    def convergence_warning(self, recent_agreement_rate: float) -> bool:
        """
        In AI-mode: high agreement = creative capture risk.
        In Human-mode: high agreement = premature closure risk (human locked up).
        Both fire True to signal the caller to inject disruptive divergence.
        """
        if self.mode == "ai":
            if recent_agreement_rate < 0.8:
                return False
            if len(self._deferral_queue) == 0 and self._interrupt_budget > 1:
                return True  # budget available but nothing being sent = capture
            return False
        else:
            # Human-mode: requires at least 2 completed segments before firing.
            # On cycle 1 with no prior trajectory, locking onto a frame is not yet
            # possible; surfacing all branches is correct behavior.
            if self._trajectory_segments_completed < 2:
                return False
            if recent_agreement_rate < 0.75:
                return False
            debt = self.attractor_debt()
            total_debt = sum(debt.values())
            return total_debt < 1.0  # converged before accumulating meaningful attractors

    def overthinking_warning(self) -> bool:
        """
        Human-mode only. Distinguishes circular rumination from monotropic deepening.

        CIRCULAR: same attractor, same content, no progress → warn.
            Last 3 visits all have delta < CIRCULAR_DELTA_FLOOR (0.08).
            If 2+ branches are circular → fires True.

        DEEPENING (monotropic flow): same attractor, new content, advancing.
            Last 2 visits both have delta >= DEPTH_DELTA_FLOOR (0.20).
            Promotes to depth_attractor_signals (positive signal, not a warning).

        The old implementation fired on deferred_count >= 3 alone, which made it
        impossible to distinguish a human building depth from a human stuck in a loop.
        Monotropism research (Murray/Lawson) is explicit: returning to the same channel
        IS the mechanism for depth — not a pathology to interrupt.
        """
        if self.mode != "human":
            return False

        circular_branches = []
        for branch in self._deferral_queue:
            if len(branch.visit_history) < CIRCULAR_VISIT_THRESHOLD:
                continue  # not enough visits to evaluate yet
            recent_deltas = [
                v.delta_score
                for v in branch.visit_history[-CIRCULAR_VISIT_THRESHOLD:]
            ]
            if all(d < CIRCULAR_DELTA_FLOOR for d in recent_deltas):
                circular_branches.append(branch)
            elif self._is_deepening(branch):
                self._promote_depth_attractor(branch)

        return len(circular_branches) >= CHRONIC_BRANCH_COUNT

    def _snapshot_trajectory(self) -> dict[str, Any]:
        return {
            "segments_completed": self._trajectory_segments_completed,
            "budget": self._interrupt_budget,
            "phase": self.relational_context.phase,
        }
