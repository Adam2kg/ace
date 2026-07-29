"""Guard: an all-unknown --providers list must fail loud, not crash opaquely."""
import pytest

from ace.agents.divergence import diverge


def test_all_unknown_providers_raises_clear_error():
    with pytest.raises(ValueError) as e:
        diverge("topic", providers=["codex"])
    msg = str(e.value)
    assert "No known divergence providers" in msg
    assert "codex" in msg              # names what the user asked for
    assert "agy" in msg                 # names what is actually available
    assert "prune" in msg               # explains why codex is gone
    assert "max_workers" not in msg     # not the old opaque failure


def test_empty_provider_list_falls_back_to_all_runners(monkeypatch):
    """providers=None means 'use every runner', not 'no runners'."""
    import ace.agents.divergence as d

    calls = []

    def fake(topic, frame_id=None):
        calls.append(topic)
        return d.DivergenceResult("fake", [], "", 0.0)

    monkeypatch.setitem(d.__dict__, "_run_agy", fake)
    monkeypatch.setattr(d, "_run_ollama", fake)
    # patch the runner table indirectly by calling with explicit known names
    diverge("t", providers=["agy", "ollama"], use_frames=False)
    assert len(calls) == 2


def test_unknown_names_are_dropped_when_at_least_one_is_known():
    """A partially-valid list still runs the valid seats (no crash, no silence)."""
    import ace.agents.divergence as d

    def fake(topic, frame_id=None):
        return d.DivergenceResult("ollama", [], "", 0.0)

    orig = d._run_ollama
    d._run_ollama = fake
    try:
        res = diverge("t", providers=["codex", "ollama"], use_frames=False)
        assert [r.provider for r in res] == ["ollama"]
    finally:
        d._run_ollama = orig
