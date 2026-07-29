"""Tests for `ace banner` — the preflight banner surfaced by the /ace skill.

The skill renders provider availability ONLY from this command's output, so the
contract matters: frames_only presets must show no external-provider rows, other
presets must show one row per active provider plus the Claude synthesis row.
"""

from click.testing import CliRunner

from ace.cli import main


def _banner(*args):
    result = CliRunner().invoke(main, ["banner", *args])
    assert result.exit_code == 0, result.output
    return result.output


def test_architecture_shows_default_provider_rows_and_coupling():
    out = _banner("--preset", "architecture")
    assert "agy" in out
    assert "Claude" in out
    # Retired seats are not in the default provider list (post-prune fleet)
    assert "codex" not in out
    assert "gemini" not in out
    # Preset coupling comes from presets.py, not a hand-maintained template
    assert "claude-sonnet-4-6" in out
    assert "claude-opus-4-8" in out


def test_frames_only_presets_show_no_external_provider_rows():
    for preset in ("frames-deep", "frames-adversarial"):
        out = _banner("--preset", preset)
        assert "Frames-only" in out
        assert "codex:" not in out
        assert "agy:" not in out
        assert "gemini:" not in out


def test_gemini_row_only_when_explicitly_requested():
    out = _banner("--preset", "architecture", "--providers", "codex,agy,gemini")
    assert "gemini" in out
    assert "deprecated" in out


def test_availability_is_checked_not_guessed(monkeypatch):
    import ace.cli as cli

    monkeypatch.setattr(cli.shutil, "which", lambda name: None)
    out = _banner("--preset", "architecture")
    assert out.count("not installed ✗") == 1  # agy (sole default external seat)

    monkeypatch.setattr(cli.shutil, "which", lambda name: f"/usr/local/bin/{name}")
    out = _banner("--preset", "architecture")
    assert "not installed" not in out
    assert out.count("available ✓") >= 2  # agy + Claude


def test_run_defaults_to_agy():
    result = CliRunner().invoke(main, ["run", "--help"])
    assert result.exit_code == 0
    # codex is quota-dead and pruned; agy is the sole default external seat
    assert "default: agy" in result.output
    assert "codex" not in result.output
