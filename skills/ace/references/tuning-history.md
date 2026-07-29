# ACE tuning history — resolved items

Split out of `../SKILL.md` on 2026-07-29 to keep it inside the 150–400 line budget.
Historical record of the first live Mirror calibration run; not needed to operate ACE.


Resolved from the first live Mirror calibration run (2 cycles, 360-editor decision),
cross-checked against an external Gemini review.

| # | Item | Verdict | Change | Status |
|---|------|---------|--------|--------|
| 1 | Frame-monoculture detector | TUNE | `frame_monoculture_risk(branches, live_provider_count)` returns False when < 2 providers contributed; CLI passes the live count (multi-provider mode only, not frames-only) | **done** + tests |
| 2 | Synthesis focus menu | VALIDATED | Keep all four options — focused panels beat the full dump | done (no change) |
| 3 | Overthinking warning | KEEP-PENDING | Needs a ≥4-cycle run with deliberate revisiting to test the 0.08 stagnation threshold | awaiting run |
| 4 | Explorer coherence floor | TUNE | New `coherence_floor` profile field + `--coherence-floor` override + `apply_coherence_floor()`. Deep Focus sets 0.70; Explorer stays 0.0 (off). Drops sub-floor branches before synthesis, never empties the set | **done** + tests |

Tests for items 1 and 4 live in `tests/test_coupling_tuning.py` (14 cases).
Run them with `python3 -m pytest`.
