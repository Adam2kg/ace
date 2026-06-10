"""
Unit tests for the two calibration TUNEs landed after the first live Mirror run:

  1. frame_monoculture_risk() must not fire when fewer than 2 divergence
     providers contributed (single-source bias vs structural monoculture).
  2. apply_coherence_floor() drops low-coherence branches before synthesis,
     with a safety guarantee that it never empties a non-empty branch set.

Also pins the pre-existing monoculture behavior so the provider gate is the
only thing that changed.
"""

import pytest

from ace.coupling.function import Branch, CouplingFunction, ScoreVector
from ace.presets import PRESETS, apply_overrides


def _branch(content: str, frame_id: str, coherence: float = 0.5,
            novelty: float = 0.5) -> Branch:
    return Branch(
        content=content,
        frame_id=frame_id,
        score=ScoreVector(novelty=novelty, coherence=coherence),
    )


# ── Item 1: provider-gated frame monoculture ──────────────────────────────────

def test_monoculture_fires_with_two_providers_one_frame():
    """Baseline: same frame across branches, >=2 providers → warning fires."""
    cf = CouplingFunction(mode="human")
    branches = [_branch(f"[gemini] idea {i}", frame_id="biology") for i in range(5)]
    assert cf.frame_monoculture_risk(branches, live_provider_count=2) is True


def test_monoculture_suppressed_with_single_provider():
    """The TUNE: identical branch set, but only 1 live provider → suppressed."""
    cf = CouplingFunction(mode="human")
    branches = [_branch(f"[gemini] idea {i}", frame_id="biology") for i in range(5)]
    assert cf.frame_monoculture_risk(branches, live_provider_count=1) is False


def test_monoculture_suppressed_with_zero_providers():
    cf = CouplingFunction(mode="human")
    branches = [_branch(f"[gemini] idea {i}", frame_id="biology") for i in range(5)]
    assert cf.frame_monoculture_risk(branches, live_provider_count=0) is False


def test_monoculture_count_none_preserves_old_behavior():
    """Passing no count (e.g. frames-only mode) leaves the detector ungated."""
    cf = CouplingFunction(mode="human")
    branches = [_branch(f"[gemini] idea {i}", frame_id="biology") for i in range(5)]
    assert cf.frame_monoculture_risk(branches) is True


def test_monoculture_false_when_frames_diverse():
    """Diverse frames → no monoculture even with enough providers."""
    cf = CouplingFunction(mode="human")
    branches = [
        _branch("[gemini] a", frame_id="biology"),
        _branch("[codex] b", frame_id="economics"),
        _branch("[gemini] c", frame_id="physics"),
        _branch("[codex] d", frame_id="systems"),
    ]
    assert cf.frame_monoculture_risk(branches, live_provider_count=2) is False


# ── Item 4: coherence floor ───────────────────────────────────────────────────

def test_coherence_floor_off_keeps_everything():
    cf = CouplingFunction(mode="human", coherence_floor=0.0)
    branches = [_branch("a", "f", coherence=0.1), _branch("b", "f", coherence=0.9)]
    surviving, dropped = cf.apply_coherence_floor(branches)
    assert len(surviving) == 2
    assert dropped == []


def test_coherence_floor_drops_below_threshold():
    cf = CouplingFunction(mode="human", coherence_floor=0.70)
    low = _branch("metaphor soup", "biology", coherence=0.50)
    high = _branch("grounded step", "engineering", coherence=0.85)
    surviving, dropped = cf.apply_coherence_floor(branches=[low, high])
    assert surviving == [high]
    assert dropped == [low]


def test_coherence_floor_keeps_unscored_branches():
    """Branches with no score can't be judged → always kept."""
    cf = CouplingFunction(mode="human", coherence_floor=0.70)
    unscored = Branch(content="no score", frame_id="f")
    low = _branch("low", "f", coherence=0.3)
    surviving, dropped = cf.apply_coherence_floor([unscored, low])
    assert unscored in surviving
    assert low in dropped


def test_coherence_floor_never_empties_set():
    """Safety: if every branch is below the floor, keep the most coherent one."""
    cf = CouplingFunction(mode="human", coherence_floor=0.70)
    branches = [
        _branch("worst", "f", coherence=0.20),
        _branch("best-of-bad", "f", coherence=0.60),
        _branch("middle", "f", coherence=0.40),
    ]
    surviving, dropped = cf.apply_coherence_floor(branches)
    assert len(surviving) == 1
    assert surviving[0].score.coherence == 0.60
    assert len(dropped) == 2


def test_coherence_floor_explicit_arg_overrides_instance():
    cf = CouplingFunction(mode="human", coherence_floor=0.0)
    branches = [_branch("a", "f", coherence=0.3), _branch("b", "f", coherence=0.9)]
    surviving, dropped = cf.apply_coherence_floor(branches, floor=0.70)
    assert [b.score.coherence for b in surviving] == [0.9]
    assert [b.score.coherence for b in dropped] == [0.3]


def test_coherence_floor_empty_input():
    cf = CouplingFunction(mode="human", coherence_floor=0.70)
    surviving, dropped = cf.apply_coherence_floor([])
    assert surviving == []
    assert dropped == []


# ── Preset / override wiring ───────────────────────────────────────────────────

def test_deep_focus_preset_sets_coherence_floor():
    assert PRESETS["human-scientific"].coherence_floor == pytest.approx(0.70)


def test_explorer_preset_leaves_floor_off():
    assert PRESETS["human-adhd"].coherence_floor == 0.0


def test_apply_overrides_sets_coherence_floor():
    base = PRESETS["human-adhd"]
    tuned = apply_overrides(base, coherence_floor=0.65)
    assert tuned.coherence_floor == pytest.approx(0.65)
    assert base.coherence_floor == 0.0  # original untouched
