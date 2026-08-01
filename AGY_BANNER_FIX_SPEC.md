# ACE skill-banner fix — make `ace.md` agy-aware + preset/provider-accurate

**Repo:** `/Users/sebastianziegler/ace`
**Status:** spec only — implement on a branch, do NOT push without confirmation.
**Author note:** written from a diagnosis session; verify every line/number below against
current source before editing (line numbers drift).

---

## TL;DR

The `ace` **Python CLI already prints a correct banner** (agy-aware, provider-aware,
frames-aware) in `ace/cli.py`. The bug is a **second, hand-maintained banner inside the
skill** `skills/ace.md` that has drifted out of sync with the engine: it is agy-blind and
ignores the selected preset's actual coupling. Fix the skill banner so it matches engine
reality — ideally by mirroring `cli.py`'s logic (or by surfacing the CLI's own output
instead of re-deriving it by hand).

The user-visible symptom was a banner row `🧭 agy: not installed ✗` — a **false negative**.
agy is installed (`~/.local/bin/agy`, on PATH; `agy --version` → 1.0.11). The row was the
LLM improvising a provider the template never had, with no real check behind it.

---

## Ground truth (verify these before editing)

**Engine is already correct:**
- `ace/cli.py:50` — `--providers` option, `default="codex,agy"` (already migrated off gemini).
- `ace/cli.py:115-127` — CLI banner: shows `frames-only` tag when `profile.frames_only`,
  else `Divergence: {divergence_model} ({provider_list}) + cognitive frames`, plus the
  synthesis model. This is the behavior the skill banner should match.
- `ace/cli.py:163` — `diverge(topic, provider_list, use_frames=not profile.frames_only)`.
- `ace/agents/divergence.py:323` — `runners = {"codex": _run_codex, "gemini": _run_gemini, "agy": _run_agy}`.
- `ace/agents/divergence.py:190` — `_run_agy()` shells out to
  `agy -p <prompt> --model "$OCTOPUS_AGY_MODEL"`; docstring: *"Replaces the dead `gemini` CLI path."*

**Preset reality (`ace/presets.py`):**
- All presets set Claude `divergence_model`/`synthesis_model`. External CLI fan-out is the
  separate `--providers` list, NOT a preset field.
- `frames_only=True` ONLY for `frames-deep` (presets.py:136) and `frames-adversarial`
  (presets.py:154). For those, there is **no multi-provider dispatch** — single provider +
  cognitive frames.
- For every other preset (architecture, debugging, design-review, looping), divergence
  **does** fan out to `--providers` (default `codex,agy`) + cognitive frames, alongside the
  Claude models. So external-provider availability IS relevant for these presets.

**The stale skill banner (`skills/ace.md`):**
- `grep -c agy skills/ace.md` → 0 (completely agy-blind).
- Preflight (~lines 78-81): only `command -v codex` and `command -v gemini`. No agy.
- Banner template (~lines 85-90): lists only 🔴 Codex / 🟡 Gemini / 🔵 Claude. No agy, no
  frames-mode awareness, no reflection of `--providers` or the preset's models.
- `ace run` invocation (~line 95): `ace run "<topic>" --preset <preset> [--human-mode] [--cycles N]`
  — does NOT pass `--providers`, so the engine uses the default `codex,agy`.

---

## Fix #1 — agy-blindness in `skills/ace.md`

1. **Preflight** (~lines 78-81): add an agy check alongside codex/gemini:
   ```bash
   printf "codex:%s\n"  "$(command -v codex  >/dev/null 2>&1 && echo available || echo missing)"
   printf "agy:%s\n"    "$(command -v agy    >/dev/null 2>&1 && echo available || echo missing)"
   printf "gemini:%s\n" "$(command -v gemini >/dev/null 2>&1 && echo available || echo missing)"
   ```
   Match the engine default order (`codex,agy`); gemini is the legacy/dead seat — keep it
   last or drop it (see note below).

2. **Banner template** (~lines 85-90): add the agy row with the 🧭 indicator and label it as
   the live Google seat. Make the status come from the preflight, never from a guess:
   ```
   🔴 Codex:  [available ✓ / quota-exceeded ✗ / not installed ✗] — divergence (technical branches)
   🧭 agy:    [available ✓ / not installed ✗] — divergence (lateral branches; live Google seat)
   🟡 Gemini: [legacy/sunset — only if installed] — divergence (deprecated)
   🔵 Claude: available ✓ — synthesis (trajectory maintenance)
   ```
   Add an explicit instruction in the skill: *"Render statuses ONLY from the preflight output
   above. Do not infer or hand-write provider availability."* (This is the LLM-paraphrase
   guard — the same failure mode produced the false agy row.)

**Gemini note:** the engine still *has* a `_run_gemini` runner, but the default `--providers`
is `codex,agy` and the docstring calls gemini "dead." Decide with the maintainer whether the
skill should still surface a Gemini row at all, or only when explicitly added to `--providers`.

---

## Fix #2 — preset / provider accuracy

The skill banner currently shows external-provider rows unconditionally. Make it reflect what
the selected preset actually does, mirroring `cli.py:115-127`:

- **`frames_only` presets (`frames-deep`, `frames-adversarial`):** no multi-provider dispatch.
  Do NOT show codex/agy/gemini availability rows (they're irrelevant). Instead show:
  `Divergence: {divergence_model} (frames-{frames_set}) — single provider, cognitive frames`.
- **All other presets:** show the external-provider rows (they ARE used via `--providers`,
  default `codex,agy`), AND show the preset's Claude coupling:
  `Divergence: {divergence_model} + ({active --providers}) + cognitive frames` /
  `Synthesis: {synthesis_model}`.

Pull the model names from `presets.get_preset(<preset>)` (`divergence_model`, `synthesis_model`,
`frames_only`, `frames_set`) so the banner can never disagree with the engine.

---

## Recommended approach (preferred over hand-editing the template)

The durable fix is to **stop maintaining a separate banner in the skill**. Two options:

- **(A) Surface the CLI's banner.** `cli.py` already prints preset + frames tag + divergence
  models + provider list + synthesis model. Have the skill run a lightweight banner/preflight
  command from the engine and display its output, instead of re-deriving it in markdown.
  If `cli.py` doesn't yet expose a no-op "print banner only" path, add one (e.g.
  `ace banner --preset <preset> --providers <list>`), and call that from the skill.
- **(B) If the banner must stay in the skill**, drive every value from the preflight + a small
  `python -c "import ace.presets as p; ..."` read of the preset, so it mirrors `cli.py` exactly.

Prefer (A): single source of truth, no future drift.

---

## Verification

- `grep -c agy skills/ace.md` → now > 0; preflight includes `command -v agy`.
- Manually run the skill's preflight block in a profile shell: agy reports `available`
  (binary at `~/.local/bin/agy`).
- For `--preset architecture`: banner shows codex/agy rows + Sonnet/Opus coupling.
- For `--preset frames-deep` / `frames-adversarial`: banner shows frames-only, NO external
  provider rows.
- Cross-check the rendered skill banner against `ace run --preset <p>` (dry/echo) so the two
  banners agree.
- Add/adjust a test if the repo has skill/banner tests (check `tests/`).

## Constraints
- Work on a branch (e.g. `fix/ace-banner-agy-aware`). Do NOT push without confirmation.
- This file (`AGY_BANNER_FIX_SPEC.md`) is scratch guidance — delete it before the final commit,
  or keep it out of the committed diff.
