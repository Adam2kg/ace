"""
Unit tests for coupling-function-as-control-plane routing (ace/coupling/routing.py).

Covers the two debate-derived rules:
  1. Synthesis model selection (regime detection + safe-failure bias toward Opus).
  2. Divergence strategy escalation (shared-blind-spot alarm on high agreement).
"""

from ace.coupling.function import Branch, ScoreVector
from ace.coupling.routing import (
    AGREEMENT_ESCALATION,
    branch_survival_rate,
    inter_frame_agreement,
    max_frame_dominance,
    recommend_routing,
)


def _branch(content: str, frame_id: str | None = None, coherence: float = 0.5,
            novelty: float = 0.6) -> Branch:
    return Branch(
        content=content,
        frame_id=frame_id,
        score=ScoreVector(novelty=novelty, coherence=coherence),
        low_trust_flag=coherence < 0.30,
    )


# ── Signal: branch_survival_rate ──────────────────────────────────────────────

def test_survival_all_coherent():
    branches = [_branch(f"distinct idea number {i}", coherence=0.7) for i in range(4)]
    assert branch_survival_rate(branches) == 1.0


def test_survival_all_low_trust():
    branches = [_branch(f"idea {i}", coherence=0.1) for i in range(4)]
    assert branch_survival_rate(branches) == 0.0


def test_survival_mixed():
    branches = [
        _branch("good one", coherence=0.7),
        _branch("good two", coherence=0.6),
        _branch("weak three", coherence=0.1),
        _branch("weak four", coherence=0.05),
    ]
    assert branch_survival_rate(branches) == 0.5


def test_survival_empty():
    assert branch_survival_rate([]) == 0.0


# ── Signal: max_frame_dominance ───────────────────────────────────────────────

def test_dominance_framed_uniform():
    branches = [_branch("x", frame_id=f) for f in ("a", "b", "c", "d")]
    assert max_frame_dominance(branches) == 0.25


def test_dominance_framed_skewed():
    branches = [_branch("x", frame_id="a") for _ in range(3)] + [_branch("y", frame_id="b")]
    assert max_frame_dominance(branches) == 0.75


def test_dominance_unframed_keyword_fallback():
    # All branches share the word "biology" → high keyword dominance.
    branches = [
        _branch("biology metaphor cellular growth"),
        _branch("biology organism evolves naturally"),
        _branch("biology ecosystem adapts slowly"),
    ]
    assert max_frame_dominance(branches) == 1.0


# ── Signal: inter_frame_agreement ─────────────────────────────────────────────

def test_agreement_identical_high():
    branches = [_branch("shared vocabulary about caching systems")] * 3
    assert inter_frame_agreement(branches) > 0.9


def test_agreement_disjoint_low():
    branches = [
        _branch("caching latency throughput pipeline"),
        _branch("narrative tension character motivation"),
        _branch("geological sediment erosion tectonic"),
    ]
    assert inter_frame_agreement(branches) < 0.2


def test_agreement_single_branch_zero():
    assert inter_frame_agreement([_branch("alone")]) == 0.0


# ── recommend_routing: regime + model selection ───────────────────────────────

def test_underdetermined_routes_to_opus():
    # Low survival + low dominance + disjoint vocab = no trajectory formed.
    branches = [
        _branch("quantum entanglement messaging substrate", frame_id="a", coherence=0.1),
        _branch("agrarian land reform cooperative", frame_id="b", coherence=0.1),
        _branch("liturgical chant acoustic resonance", frame_id="c", coherence=0.2),
        _branch("supply chain blockchain provenance", frame_id="d", coherence=0.15),
    ]
    rec = recommend_routing(branches)
    assert rec.synthesis_model == "opus"
    assert rec.regime == "underdetermined"


def test_ambiguous_band_routes_to_opus():
    # survival in [0.40, 0.50) → safe-failure bias to Opus even with some dominance.
    branches = [
        _branch("alpha idea one", frame_id="a", coherence=0.7),
        _branch("alpha idea two", frame_id="a", coherence=0.6),
        _branch("weak three", frame_id="b", coherence=0.1),
        _branch("weak four", frame_id="b", coherence=0.1),
        _branch("weak five", frame_id="c", coherence=0.1),
    ]
    # survival = 2/5 = 0.40 → not < 0.40, but < 0.50 → ambiguous
    rec = recommend_routing(branches)
    assert rec.synthesis_model == "opus"
    assert rec.regime == "ambiguous"


def test_low_survival_high_dominance_routes_opus_with_correct_rationale():
    # Single-frame low-coherence noise: survival < 0.40 but dominance = 1.0.
    # Must route to Opus (safe-failure bias) WITHOUT claiming the [0.40,0.50) band.
    branches = [_branch(f"shallow frame branch {i}", frame_id="a", coherence=0.1) for i in range(8)]
    rec = recommend_routing(branches)
    assert rec.synthesis_model == "opus"
    assert rec.regime == "ambiguous"
    assert rec.signals["branch_survival_rate"] < 0.40
    assert "ambiguous band" not in rec.rationale  # must not misdescribe its own number


def test_converging_routes_to_sonnet():
    # High survival = trajectory forming → convergent model.
    branches = [
        _branch("coherent thread one about routing", frame_id="a", coherence=0.8),
        _branch("coherent thread two about routing", frame_id="a", coherence=0.7),
        _branch("coherent thread three routing logic", frame_id="b", coherence=0.75),
        _branch("coherent thread four routing design", frame_id="b", coherence=0.7),
    ]
    rec = recommend_routing(branches)
    assert rec.synthesis_model == "sonnet"
    assert rec.regime == "converging"


# ── recommend_routing: divergence escalation ──────────────────────────────────

def test_escalation_fires_on_high_agreement():
    branches = [_branch("identical shared blind spot vocabulary here", frame_id="a", coherence=0.7)] * 4
    rec = recommend_routing(branches)
    assert rec.escalate_divergence is True
    assert rec.signals["inter_frame_agreement"] > AGREEMENT_ESCALATION


def test_no_escalation_on_diverse_branches():
    branches = [
        _branch("caching latency throughput", frame_id="a", coherence=0.7),
        _branch("narrative tension character", frame_id="b", coherence=0.7),
        _branch("geological erosion tectonic", frame_id="c", coherence=0.7),
    ]
    rec = recommend_routing(branches)
    assert rec.escalate_divergence is False
