"""
Coupling-function-as-control-plane: synthesis-model and divergence-strategy routing.

Both routing decisions were settled by adversarial debate (a 3-round model-routing
debate and a 2-round divergence-strategy debate) and are computed entirely from
signals ACE already tracks — no new measurement, no extra LLM call.

Rule 1 — SYNTHESIS MODEL SELECTION (from the model-routing debate):
  Detect the synthesis regime from the post-divergence branch set.
    - branch_survival_rate < 0.40 AND max_frame_dominance < 0.60
        → the convergence target is underdetermined; synthesis is secretly a
          second divergence → route to a holistic model (Opus) that holds
          implausible combinations alive instead of pruning them early.
    - otherwise → a trajectory is forming → a convergent model (Sonnet/Haiku)
      is cheaper and correct, because its early-pruning is an asset here.
  Safe-failure bias: the dangerous mis-route is underdetermined → convergent
  (it launders an open question as a confident, premature answer). So when the
  signals are ambiguous, prefer Opus. The failure mode of the rule is made safe,
  not eliminated.

Rule 2 — DIVERGENCE STRATEGY ESCALATION (from the divergence-strategy debate):
  Default to synthetic diversity (one model + cognitive frames). Today's model
  families share an overlapping training corpus, so swapping families buys only
  modest orthogonality at clustered-fragility cost. Escalate to distribution
  diversity (a different model family) only when the branches agree too much —
  a shared-blind-spot alarm — because that is the regime where one model's
  priors are visibly capping the divergence.
    - inter_frame_agreement > 0.80 → escalate
"""
from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations

from ace.coupling.function import Branch, CouplingFunction

# ── Thresholds (debate-derived; tune from observed sessions) ──────────────────
SURVIVAL_UNDERDETERMINED = 0.40   # below this (+ low dominance) = underdetermined target
FRAME_DOMINANCE_CEILING = 0.60    # a single dominant frame above this = trajectory forming
SURVIVAL_AMBIGUOUS = 0.50         # safe-failure band: [0.40, 0.50) still routes to Opus
AGREEMENT_ESCALATION = 0.80       # inter-branch agreement above this = shared blind spot

COHERENCE_SURVIVAL_FLOOR = 0.30   # a branch "survives" pruning at/above this coherence


@dataclass
class RoutingRecommendation:
    """What the coupling function recommends for the synthesis step and next cycle."""
    synthesis_model: str            # "opus" | "sonnet"
    regime: str                     # "underdetermined" | "ambiguous" | "converging"
    escalate_divergence: bool       # True = add a different model family next cycle
    signals: dict[str, float] = field(default_factory=dict)
    rationale: str = ""


def branch_survival_rate(branches: list[Branch]) -> float:
    """Fraction of branches that clear the coherence floor (i.e. survive pruning)."""
    if not branches:
        return 0.0
    survived = sum(
        1 for b in branches
        if not b.low_trust_flag and b.effective_score.coherence >= COHERENCE_SURVIVAL_FLOOR
    )
    return survived / len(branches)


def max_frame_dominance(branches: list[Branch]) -> float:
    """Share of branches belonging to the single most common frame.

    Uses frame_id when any branch is framed; otherwise falls back to the most
    common keyword's prevalence as a proxy for metaphor-domain dominance.
    """
    if not branches:
        return 0.0
    framed = [b.frame_id for b in branches if b.frame_id]
    if framed:
        counts: dict[str, int] = {}
        for fid in framed:
            counts[fid] = counts.get(fid, 0) + 1
        return max(counts.values()) / len(branches)

    # Unframed fallback: most prevalent keyword across branches.
    kw_doc_count: dict[str, int] = {}
    for b in branches:
        for kw in CouplingFunction._extract_keywords(b.content):
            kw_doc_count[kw] = kw_doc_count.get(kw, 0) + 1
    if not kw_doc_count:
        return 0.0
    return max(kw_doc_count.values()) / len(branches)


def inter_frame_agreement(branches: list[Branch]) -> float:
    """Mean pairwise keyword Jaccard similarity across branches.

    High agreement = branches converge on the same vocabulary = a likely shared
    blind spot (one model's priors capping the divergence).
    """
    if len(branches) < 2:
        return 0.0
    kw_sets = [CouplingFunction._extract_keywords(b.content) for b in branches]
    sims = []
    for a, b in combinations(kw_sets, 2):
        union = a | b
        if not union:
            continue
        sims.append(len(a & b) / len(union))
    return sum(sims) / len(sims) if sims else 0.0


def recommend_routing(branches: list[Branch]) -> RoutingRecommendation:
    """Compute synthesis-model and divergence-strategy routing from branch signals."""
    survival = branch_survival_rate(branches)
    dominance = max_frame_dominance(branches)
    agreement = inter_frame_agreement(branches)

    signals = {
        "branch_survival_rate": round(survival, 3),
        "max_frame_dominance": round(dominance, 3),
        "inter_frame_agreement": round(agreement, 3),
    }

    # Rule 1 — synthesis model selection (with safe-failure bias toward Opus).
    if survival < SURVIVAL_UNDERDETERMINED and dominance < FRAME_DOMINANCE_CEILING:
        model, regime = "opus", "underdetermined"
        why = (
            f"survival {survival:.2f} < {SURVIVAL_UNDERDETERMINED} and dominance "
            f"{dominance:.2f} < {FRAME_DOMINANCE_CEILING}: no trajectory has formed — "
            "treat synthesis as a second divergence and use a holistic model."
        )
    elif survival < SURVIVAL_AMBIGUOUS:
        model, regime = "opus", "ambiguous"
        if survival < SURVIVAL_UNDERDETERMINED:
            # Low survival but the underdetermined gate's dominance clause did not
            # trigger (e.g. a single dominant frame) — can't cleanly distinguish
            # underdetermined-target from monoculture, so fall back to the bias.
            why = (
                f"survival {survival:.2f} < {SURVIVAL_UNDERDETERMINED} but dominance "
                f"{dominance:.2f} ≥ {FRAME_DOMINANCE_CEILING} (no frame diversity to "
                "confirm an underdetermined target): safe-failure bias prefers Opus."
            )
        else:
            why = (
                f"survival {survival:.2f} is in the ambiguous band "
                f"[{SURVIVAL_UNDERDETERMINED}, {SURVIVAL_AMBIGUOUS}): safe-failure bias "
                "prefers Opus to avoid laundering an open question as premature closure."
            )
    else:
        model, regime = "sonnet", "converging"
        why = (
            f"survival {survival:.2f} ≥ {SURVIVAL_AMBIGUOUS}: a trajectory is forming — "
            "a convergent model's early-pruning is an asset and is cheaper."
        )

    # Rule 2 — divergence strategy escalation.
    escalate = agreement > AGREEMENT_ESCALATION
    if escalate:
        why += (
            f" Inter-branch agreement {agreement:.2f} > {AGREEMENT_ESCALATION}: shared "
            "blind spot likely — escalate to a different model family next cycle."
        )

    return RoutingRecommendation(
        synthesis_model=model,
        regime=regime,
        escalate_divergence=escalate,
        signals=signals,
        rationale=why,
    )
