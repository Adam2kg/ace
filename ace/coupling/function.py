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
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ReceptivityState(Enum):
    OPEN = "open"            # actively soliciting divergence
    NEUTRAL = "neutral"      # standard operating
    CONSOLIDATING = "consolidating"  # mid-synthesis, budget frozen
    LOCKED = "locked"        # trajectory committed


@dataclass
class ScoreVector:
    """
    Metadata from the divergence scoring pass (populated by adhd-style scoring).
    Used by the coupling function as weights, never as prune gates.

    novelty:          0-1, distance from the obvious default answer
    coherence:        0-1, how well the branch addresses the stated problem
    frame_saturation: 0-1, how much the frame explains the output rather than
                      the problem — high saturation → frame drift risk in
                      multi-round sessions
    """
    novelty: float = 0.5
    coherence: float = 0.5
    frame_saturation: float = 0.0


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

    # ── Interrupt budget ─────────────────────────────────────────────────────

    def can_interrupt(self, emergency: bool = False) -> bool:
        if emergency:
            cost = 2
        else:
            cost = 1
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
        branch.deferred_count += 1
        branch.receptivity_at_deferral = self._receptivity
        branch.trajectory_context = self._snapshot_trajectory()
        self._deferral_queue.append(branch)

    def integrate(self, branch: Branch) -> None:
        """Mark a branch as accepted into the trajectory."""
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
            "relational_context": {
                "avg_response_time": self.relational_context.avg_response_time(),
                "accepted_count": len(self.relational_context.accepted_signatures),
                "deferred_count": len(self.relational_context.deferred_signatures),
                "phase": self.relational_context.phase,
            },
        }

    # ── adhd score integration ────────────────────────────────────────────────

    def synthesis_weight(self, branch: Branch) -> float:
        """
        Priority weight for synthesis: novelty × sigmoid(coherence).
        Used to order branches for the synthesis agent — high novelty + high
        coherence surfaces first. Unscored branches receive neutral weight 1.0.
        Does NOT prune — a weight of 0.1 still enters the synthesis pass.
        """
        if branch.score is None:
            return 1.0
        coherence_sigmoid = 1.0 / (1.0 + math.exp(-10.0 * (branch.score.coherence - 0.5)))
        return branch.score.novelty * coherence_sigmoid

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
            # Opening up: restore OPEN receptivity and high budget
            self._receptivity = ReceptivityState.OPEN
            self._interrupt_budget = max(self._interrupt_budget, self.base_interrupt_budget)
        elif new_mode == "ai" and old_mode == "human":
            # Narrowing: move to NEUTRAL, synthesis can now drive
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
            # Human-mode: premature convergence = human locking onto unexamined frame
            if recent_agreement_rate < 0.75:
                return False
            # High agreement AND low debt = human resolved without exploring alternatives
            debt = self.attractor_debt()
            total_debt = sum(debt.values())
            return total_debt < 1.0  # converged before accumulating meaningful attractors

    def overthinking_warning(self) -> bool:
        """
        Human-mode only: fires when the same attractor hash keeps re-emerging
        after nominal closure (re-emergence debt). Signals trajectory clutch:
        force binary closure before resuming divergence.

        Detects: branches that have been deferred 3+ times are still in queue,
        indicating the human cannot close them — half-open integration loops.
        """
        if self.mode != "human":
            return False
        chronic = [b for b in self._deferral_queue if b.deferred_count >= 3]
        return len(chronic) >= 2  # two or more chronically un-closable attractors

    def _snapshot_trajectory(self) -> dict[str, Any]:
        return {
            "segments_completed": self._trajectory_segments_completed,
            "budget": self._interrupt_budget,
            "phase": self.relational_context.phase,
        }
