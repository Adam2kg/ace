# Frame catalog — all 15 cognitive frames

Source of truth: `FRAMES` in `ace/agents/divergence.py`. A frame is **not a persona to mimic** —
it is a goal-function redirect that changes which *class of question* the model asks. Frames are
injected by `_build_framed_prompt` as a `COGNITIVE FRAME — <NAME>:` block before the topic.

Re-verify the list: `grep -n '^    "' ace/agents/divergence.py | head -40` (T1)

## The 15 frames

| Frame | What it redirects toward | When it bites hardest |
|---|---|---|
| `hardware-engineer` | Latency, memory layout, bus topology, timing budgets | Performance decisions, storage/index choices, anything with a hot path |
| `regulator` | What must be provable, traceable, or refusable | Compliance, audit trails, GDPR/PII boundaries, data retention |
| `ten-year-old` | Naive but unencumbered approaches; ignore convention | When the team has over-engineered; when the obvious cheap answer is invisible |
| `adversary` | Exploits, sabotage, failure — then inverted into defenses | Threat modelling, security review, trust boundaries |
| `biology` | Immune systems, plasticity, cell signaling, evolution, gut flora | Self-healing systems, adaptive/decentralized designs, resilience |
| `logistics` | Queues, batching, JIT, hub-and-spoke, returns, last-mile | Pipelines, job scheduling, backpressure, throughput problems |
| `game-design` | Loops, rewards, friction, save-states, speedrun tricks | UX, onboarding, retention, anything where a human is "playing" the system |
| `markets` | Buyers, sellers, market-makers, auctions, clearing | Resource allocation, prioritization, multi-tenant contention |
| `inversion` | "How would we guarantee NOT-X" — then negate back | Stuck problems; when every idea sounds the same |
| `extreme-zero` | No money, no team, one hour — crudest load-bearing version | Scoping, MVP definition, killing gold-plating |
| `extreme-infinite` | Infinite compute/engineers/decade — maximalist version | Long-horizon architecture, finding the ceiling of an approach |
| `remove-assumption` | Delete the thing everyone treats as fixed (framework, DB, req/resp) | Migration decisions, "why do we even have this layer" |
| `speedrunner` | Glitches, skips, out-of-bounds, abusive-but-legal paths | Finding shortcuts; also a cheap adversarial proxy |
| `ant-colony` | No central planner; dumb agents, local rules, pheromones | Distributed systems, emergent coordination, eventual consistency |
| `ops-3am` | The on-call engineer paged at 3am; runbook-shaped solutions | Operability, alerting, "which design lets me sleep" |

## Provider affinity

`FRAME_PROVIDER_AFFINITY` assigns frames so they **amplify** a seat's native bias rather than
fight it. `_select_frame(provider, used_frames)` walks the seat's list and takes the first unused
frame; if all are used it falls back to any unused frame in `FRAMES`; if none remain it returns
`None` (unframed). No two seats in one cycle get the same frame.

| Seat | Frames |
|---|---|
| `agy` | biology, markets, ten-year-old, regulator, hardware-engineer, ops-3am, extreme-zero, speedrunner |
| `ollama` | game-design, logistics, ant-colony, adversary, inversion, extreme-infinite, remove-assumption |

Note: after the prune, `codex` and `gemini` were deleted and their frames were redistributed to the
two surviving seats. Two assignments (`speedrunner`, `remove-assumption`) remain empirically
disputed — they reflect a 2-1 majority position from the original frames-vs-providers debate
(`docs/debate-frames-vs-providers.md`).

## Frames-only sets

Used when `profile.frames_only = True` — no external dispatch happens at all.

| Constant | Preset | Frames |
|---|---|---|
| `FRAMES_DEEP_SET` | `frames-deep` | regulator, ten-year-old, inversion, remove-assumption, extreme-zero |
| `FRAMES_ADVERSARIAL_SET` | `frames-adversarial` | adversary, inversion, ops-3am, extreme-zero, remove-assumption |

`frames-adversarial` sets `convergence_warning_enabled = False` on purpose: adversarial frames
produce *intentional* convergence (several frames legitimately land on the same attack), so a
convergence warning there would be a false positive.

**Open item (do not oversell):** `FRAMES_DEEP_SET` and `FRAMES_ADVERSARIAL_SET` are defined in
`divergence.py` and named in the preset descriptions, but on this branch `diverge()` does not read
them — `use_frames=False` is passed for frames-only presets, so no frame block is injected by the
engine and the frames-only presets currently act as "single provider, no frame injection at the
engine layer". Verify before relying on it:
`grep -n 'FRAMES_DEEP_SET\|FRAMES_ADVERSARIAL_SET' -r ace/` (T1, checked 2026-07-29 — only the
definition site matched).

## Frame saturation

`_score_branches` computes `frame_saturation` = overlap between a branch's words and the frame
prompt's words. High saturation means the branch is echoing the frame's vocabulary rather than
applying its logic — a "the immune system is like a cache" branch with no mechanism. It is recorded
on the `ScoreVector` but is **not** used to prune. Read it as a quality tell when scanning branches.
