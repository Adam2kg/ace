# ACE session diagnosis — coupling and synthesis misbehavior

Split out of `../SKILL.md` on 2026-07-29 for the 150–400 line budget.

**Scope:** this is about the *coupling function and synthesis* behaving oddly.
For provider **seat health** (agy/ollama/openai up, auth, quota, empty output),
use the sibling skill `ace-doctor` instead — different failure domain.


### "Every branch feels like the same idea from a different angle"

Frame monoculture. ACE should have warned. If it didn't fire:
- Check if `--preset` is a human-mode preset (monoculture detection is always active)
- Add a different seed topic next cycle: "What would someone who DISAGREES with all of this say?"
- Try `--preset frames-adversarial` for one cycle to force perspective diversity

### "The synthesis panel is useless / feels like noise"

Two causes:
1. **Too many branches** — reduce `--cycles` or pick focus option [1] or [3] instead of [4]
2. **Wrong calibration** — Explorer for scattered thinking, Deep Focus for precision work. If you're in Deep Focus during open-ended exploration, synthesis will try to converge prematurely.

### "ACE keeps warning about overthinking but I'm not looping"

The overthinking warning fires when ≥2 branches have been visited ≥3 times with stagnant
progress delta (< 0.08) across all recent visits. If this fires on genuine deepening:
- This is a calibration gap — Explorer uses a lower depth delta floor (0.15) to better
  distinguish deepening from looping
- Switch to Explorer or set `--preset human-adhd` explicitly
- *Still pending — the one calibration run (2 cycles) never triggered re-emergence, so the*
  *0.08 stagnation threshold is untested. Needs a ≥4-cycle run with deliberate revisiting.*

### "Nothing is getting deferred / attractor debt is always 0"

This means all branches are being integrated immediately — coupling function isn't accumulating
anything. Two causes:
1. Topic is genuinely well-bounded (good)
2. Budget is too high and the coupling function never needs to defer anything — try reducing
   `--cycles` or use `--preset debugging` for tighter budget

### "The coupling state shows high deferred_count but nothing is surfacing"

Debt threshold is too high for the session. Adjustable:
```bash tier=T3 verified=2026-07-29
ace run "<topic>" --preset human-adhd --debt-threshold 1.5 --human-mode
```
Or use Deep Focus which has a threshold of 6.0 (patient); Explorer uses 2.0 (reactive).

---

