# Debate: Frames vs Providers — ACE Divergence Architecture

**Topic:** Should ACE's divergence engine use cognitive frames (uditakhourii/adhd), multi-provider dispatch, or both combined?

**Format:** 3 rounds, 3 external participants (Gemini CLI, Claude Sonnet subagent, Claude Codex subagent). Claude moderator.

**uditakhourii/adhd context:** TypeScript tree-of-thought engine. N parallel branches each under a cognitive frame (hardware-engineer, adversary, ant-colony, etc.), single LLM. Score + cluster + prune + deepen. 771 stars, published npm package, production-tested. Key insight from research: adhd solves *within-provider* divergence width; ACE's multi-provider dispatch solves *cross-provider* distribution diversity. Independent axes.

---

## Verdict

**Combined (Option C) wins unanimously** — all participants, all three rounds.

Providers-only never wins: it wastes within-provider variance that frames extract cheaply.
Frames-only wins under seven specific conditions (see presets section).

---

## Key Concepts Coined

**Attentional narrowing** (Gemini, Round 3) — the correct refinement of "persona collapse." Goal-function frames do not cause persona collapse (character mimicry). They cause attentional narrowing: systematic suppression of out-of-frame considerations. This is recoverable via coverage complementarity in the frame set and convergence detection in the coupling function.

**Coverage complementarity** (Sonnet, Round 3) — frame sets must be designed so each frame's blind spot is another frame's vantage point. A regulator frame that ignores performance is offset by an ops-3am frame that ignores everything except reliability.

**Frame saturation** (Qwen/Codex, Round 3) — measures how much of a branch's content was predictable from the frame alone. High saturation = the frame is explaining the output, not the problem. Essential for multi-round ACE sessions where frame drift accumulates. Add as `frame_saturation: f32` to ScoreVector.

**De-framing Reset** (Gemini CLI, Round 3) — when receptivity delta across frames ≈ 0 while novelty scores are flat, ACE triggers frame rotation rather than continuing into premature convergence.

---

## The Integration Architecture

### adhd owns frames. ACE owns orchestration.

This was the Codex position in Round 2 and was adopted unanimously by Round 3.

Rejected alternative: ACE passes a frame_manifest into adhd. This couples the systems at the frame-selection level. Instead, ACE passes constraint_hints (domain context) that adhd uses to weight its own frame selection.

### Canonical Data Flow

```
ACE → adhd (input):
  problem: String
  max_branches: int
  constraint_hints: String[]   # domain context for frame weighting (e.g. "regulatory problem")

adhd → ACE (Phase 1 exit — before any pruning):
  branches: Branch[]           # full, unpruned
  novelty: Map<BranchId, f32>
  coherence: Map<BranchId, f32>
  semantic_distance: Matrix<f32>?   # optional, for convergence detection
  frames_used: Frame[]         # telemetry only, not a gate

ACE coupling function:
  synthesis_weight[b] = novelty[b] × sigmoid(coherence[b])
  low_trust[b]        = coherence[b] < 0.3  → flag for human review, do NOT discard
  convergence         = mean(semantic_distance) < θ → ConvergenceWarning + frame rotation
  monoculture_risk    = all high-weight branches share same frame_tag → FrameRotationSignal
```

ACE **never prunes** on adhd scores. Scores are weights and metadata — the coupling function decides disposition.

### Branch Datatype Delta (backward-compatible)

```python
@dataclass
class Branch:
    content: str
    timestamp: float
    decay_constant: float = 0.1
    deferred_count: int = 0
    source: str = "unknown"
    source_signature: str = "unknown"
    # adhd integration fields — all optional, backward-compatible
    frame_id: str | None = None          # which frame generated this branch
    adhd_novelty: float | None = None    # from adhd scoring pass
    adhd_coherence: float | None = None  # from adhd scoring pass
    low_trust_flag: bool = False         # propagates to synthesis output
```

### Double Synthesis: Resolved

adhd has its own Phase 2 (score + cluster + prune) that would run BEFORE ACE's coupling function sees branches. These fitness functions conflict: adhd removes within-session redundancy; ACE values attractor debt across the full search space (lonely branches matter). Solution: ACE forks adhd at Phase 1 exit (raw divergence), not Phase 2 output. The two synthesis layers run in parallel and merge — they do not chain.

---

## The Provider-Frame Affinity Map

Frame assignments should **amplify** provider-native biases, not override them. A hardware-engineer frame on Codex deepens its existing bias. A biology frame on Gemini amplifies its emergent-complexity strengths.

| Frame | Provider | Rationale | Consensus |
|-------|----------|-----------|-----------|
| biology | Gemini | Multi-domain systemic connections | Unanimous |
| markets | Gemini | Ecosystem/complexity reasoning | Unanimous |
| ten-year-old | Gemini | Wide-coverage analogical reasoning | Unanimous |
| regulator | Gemini | Ecosystem knowledge, liability reasoning | R3 consensus (Codex conceded) |
| ant-colony | Qwen | Non-Western emergence/systems models | Unanimous |
| adversary | Qwen | Adversarial/stress-test orientation | Unanimous |
| inversion | Qwen | Boundary condition & assumption audit | Unanimous |
| extreme-infinite | Qwen | Scale/optimization bias | Unanimous |
| ops-3am | Codex | Concrete implementation + reliability | Unanimous |
| extreme-zero | Codex | Constraint-satisfaction, min viable | Unanimous |
| hardware-engineer | Codex* | Implementation-grounded (disputed) | 2-1 vs Qwen |
| speedrunner | **Disputed** | Codex (Gemini CLI) vs Qwen (Claude×2) | Unresolved |
| remove-assumption | **Disputed** | Codex (Codex) vs Qwen (Sonnet) | Unresolved |

*Two frames remain empirically unresolved. Settle by running both assignments and comparing attractor debt concentration after 3 sessions.

---

## Frames-Only: A First-Class Preset

Frames-only (single provider, multiple frames, no multi-provider dispatch) beats combined under these conditions:

1. **Conceptual/evaluative problems** — requirements elicitation, assumption surfacing, pre-mortem analysis. Depth of questioning, not breadth of approach.
2. **Budget ceiling** < $0.10/query or > 1000 queries/day
3. **Latency ceiling** < 2s (synchronous path required)
4. **Single-provider context** — quota exhaustion, restricted deployment, key unavailability *(directly relevant: this repo's `fix/gemini-exec-quota-fallback` branch)*
5. **Data trust boundary** — proprietary data cannot leave a single-provider boundary
6. **Reproducibility required** — regulated environments (legal, medical, financial) requiring auditable outputs
7. **Adversarial threat modeling** — consistent provider blind spots preferable to variable cross-provider gaps

### New ACE Presets

```python
"frames-deep": CouplingProfile(
    # Condition 1-5: conceptual, budget-constrained, trust-bounded
    # Single provider, multiple frames, no multi-provider dispatch
    ...
)

"frames-adversarial": CouplingProfile(
    # Conditions 6-7: reproducibility, threat modeling
    # Fixed provider, adversary + inversion + remove-assumption frames only
    ...
)
```

---

## What Changes in ACE

| File | Change |
|------|--------|
| `ace/agents/divergence.py` | Each provider call gets a frame from the affinity map, not a raw topic string |
| `ace/coupling/function.py` | Four new score-consuming behaviors: novelty weight, coherence gate, convergence detection, monoculture detection |
| `ace/coupling/function.py` | `Branch` datatype: four new optional fields |
| `ace/presets.py` | Two new presets: `frames-deep`, `frames-adversarial` |
| `ace/presets.py` | Affinity map as a constant: `FRAME_PROVIDER_AFFINITY: dict[str, str]` |
| Provider fallback path | On quota hit → gracefully route to `frames-deep` with available provider |

---

## Open Questions

1. **Frame saturation measurement** — how to compute it efficiently without a second LLM call? Cosine similarity between branch text and frame prompt is a cheap approximation.
2. **Semantic distance matrix** — which embedding model? In-process (sentence-transformers) or API-based? In-process preferred for latency.
3. **Speedrunner and remove-assumption** — run both assignments across 3 sessions, compare attractor debt concentration. Empirical resolution.
4. **Convergence threshold θ** — what value? Start at 0.3 cosine similarity, tune per preset.
