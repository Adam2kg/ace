"""
Divergence agent — ADHD-mode.

Maps onto Octopus providers:
  🔴 Codex  → technical feasibility, implementation angles
  🟡 Gemini → lateral thinking, ecosystem connections, analogies

Both run in parallel. Each produces a list of Branch candidates.
The coupling function decides which get integrated vs. deferred.

The agent's "errors" (tangents, false starts, premature connections)
are structurally necessary — they are the entropy injection that prevents
the synthesis agent from converging to local minima. Do not optimize them away.
"""

from __future__ import annotations

import os
import re
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

from ace.coupling.function import Branch, ScoreVector

# ── Cognitive frames (ported from uditakhourii/adhd frames.ts) ────────────────
# Each frame redirects the provider's goal-function — not a persona to mimic,
# but a vantage point that changes what class of question gets asked.
# This is synthetic diversity; provider dispatch is distribution diversity.
# Both axes are needed; they are not interchangeable.

FRAMES: dict[str, str] = {
    "hardware-engineer": (
        "You think in latency, memory layout, and physical constraints. Re-ask this problem "
        "as if it were a hardware/firmware problem. What does the bus topology, cache, or "
        "timing budget tell you?"
    ),
    "regulator": (
        "You audit systems for compliance and failure modes. What ideas surface when you ask: "
        "what must be provable, traceable, or refusable here?"
    ),
    "ten-year-old": (
        "You are a curious 10-year-old who has never seen software before. Describe naive but "
        "unencumbered approaches. Ignore convention."
    ),
    "adversary": (
        "You are a hostile competitor or attacker. Generate approaches that exploit, fail, or "
        "sabotage the obvious solution. Then invert each into a defensive idea."
    ),
    "biology": (
        "Transplant a mechanism from biology — immune systems, neural plasticity, cell signaling, "
        "evolution, gut flora — and force-fit it onto this engineering problem."
    ),
    "logistics": (
        "Steal mechanisms from logistics: queues, batching, just-in-time, hub-and-spoke, "
        "returns, last-mile. Apply them literally to this problem."
    ),
    "game-design": (
        "Approach this as a game designer. What are the loops, rewards, friction, save-states, "
        "speedrun tricks? Treat the user or system as a player."
    ),
    "markets": (
        "Treat the problem as a market. Who are the buyers, sellers, market-makers? What does "
        "an auction, a futures contract, or a clearing house look like here?"
    ),
    "inversion": (
        "Ask the OPPOSITE question. If the goal is X, brainstorm 'how would we guarantee NOT-X' "
        "— then negate each answer back into an idea."
    ),
    "extreme-zero": (
        "You have no money, no team, one hour. What is the crudest version that still does the "
        "load-bearing thing? Hacks, hardcoded values, manual loops welcome."
    ),
    "extreme-infinite": (
        "You have infinite compute, infinite engineers, a decade. What does the maximalist "
        "version look like? What would only be possible at that scale?"
    ),
    "remove-assumption": (
        "Name the thing everyone treats as fixed in this problem (the framework, the database, "
        "the request/response model). Imagine it is gone. Generate ideas that only exist in that world."
    ),
    "speedrunner": (
        "You are a speedrunner. Find glitches, skips, out-of-bounds tricks, frame-perfect "
        "shortcuts. What is the abusive-but-legal path through this problem?"
    ),
    "ant-colony": (
        "No central planner. Many dumb agents, local rules, pheromone trails. How does the "
        "problem solve itself emergently?"
    ),
    "ops-3am": (
        "You are the on-call engineer woken at 3am when this thing breaks. What design would "
        "let you not get paged? What is the runbook-shaped solution?"
    ),
}

# Provider → cognitive frame affinity map (debate verdict, June 2026).
# Assignment principle: frames should AMPLIFY provider-native bias, not override it.
# Two frames remain empirically disputed (speedrunner, remove-assumption);
# assignments below reflect the 2-1 majority position.
FRAME_PROVIDER_AFFINITY: dict[str, list[str]] = {
    # Post-prune fleet (2026-07): codex (quota-dead) and gemini CLI (retired)
    # are gone; their frames are redistributed to the surviving seats.
    # agy = live Gemini-family seat (lateral + technical frames).
    # ollama = local Qwen (structural/adversarial frames; qwen seat folded in).
    "agy":    ["biology", "markets", "ten-year-old", "regulator",
               "hardware-engineer", "ops-3am", "extreme-zero", "speedrunner"],
    "ollama": ["game-design", "logistics", "ant-colony", "adversary",
               "inversion", "extreme-infinite", "remove-assumption"],
}

# Frames used for frames-only presets (no multi-provider dispatch).
FRAMES_DEEP_SET = ["regulator", "ten-year-old", "inversion", "remove-assumption", "extreme-zero"]
FRAMES_ADVERSARIAL_SET = ["adversary", "inversion", "ops-3am", "extreme-zero", "remove-assumption"]


@dataclass
class DivergenceResult:
    provider: str
    branches: list[Branch]
    raw_output: str
    elapsed: float
    available: bool = True
    error: str = ""
    frame_id: str | None = None   # which frame was applied


def _build_framed_prompt(topic: str, frame_id: str | None, suffix: str) -> str:
    """Inject the frame as a goal-function redirect before the output instructions."""
    frame_block = ""
    if frame_id and frame_id in FRAMES:
        frame_block = f"\nCOGNITIVE FRAME — {frame_id.upper()}:\n{FRAMES[frame_id]}\n"
    return (
        "IMPORTANT: You are running as a divergence agent in an ACE (Asymmetric Cognitive "
        "Equilibrium) session. Skip all skills and preambles. Respond directly.\n"
        f"{frame_block}\n"
        f"TOPIC: {topic}\n\n"
        f"{suffix}"
    )


def _ollama_model() -> str:
    """First locally-installed Ollama model, or the configured override."""
    env = os.environ.get("ACE_OLLAMA_MODEL") or os.environ.get("OCTOPUS_OLLAMA_MODEL")
    if env:
        return env
    try:
        out = subprocess.run(
            ["ollama", "list"], capture_output=True, text=True, timeout=10,
        ).stdout.splitlines()
        if len(out) > 1:
            return out[1].split()[0]
    except (subprocess.TimeoutExpired, FileNotFoundError, IndexError):
        pass
    return "qwen2.5-coder:7b"


_ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[a-zA-Z]|\x1b[()][0-9A-Za-z]|[\x00-\x08\x0b-\x1f]")

# Hardened provider adapters (standalone, octopus-free — see
# ~/.claude/scripts/adapters/HARVEST.md). Runners shell out to these so
# invocation quirks (auth, sandboxing, fail-closed pulls) live in ONE place.
_ADAPTERS = os.path.expanduser("~/.claude/scripts/adapters")


def _run_ollama(topic: str, frame_id: str | None = None) -> DivergenceResult:
    """Local divergence runner — zero external dependency, no API cost.

    Calls the hardened `ollama.sh` adapter: FAIL-CLOSED on absent models (no
    silent auto-pull), think:false + capped tokens, non-empty output enforced.
    Zombie gate: empty output or non-zero exit => available=False, never a
    silently-empty "healthy" seat.
    """
    start = time.time()
    instruction = _build_framed_prompt(
        topic, frame_id,
        "Output: numbered list of distinct branches (ideas, approaches, angles). "
        "Each branch: one sentence label + one sentence rationale. "
        "Minimum 4 branches. Prioritize specificity over generality. "
        "Push past the obvious — the first 3 ideas you'd think of are banned.",
    )
    env = {**os.environ, "OLLAMA_MODEL": _ollama_model(), "OLLAMA_NUM_PREDICT": "1024"}
    try:
        result = subprocess.run(
            [os.path.join(_ADAPTERS, "ollama.sh"), instruction],
            capture_output=True, text=True, timeout=300, env=env,
        )
        raw = _ANSI_RE.sub("", result.stdout).strip()
        elapsed = time.time() - start
        if result.returncode != 0 or not raw:
            return DivergenceResult("ollama", [], raw, elapsed, available=False,
                                    error=(result.stderr.strip() or "empty_output")[:200],
                                    frame_id=frame_id)
        branches = _parse_branches(raw, "ollama", frame_id)
        return DivergenceResult("ollama", branches, raw, elapsed, frame_id=frame_id)
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return DivergenceResult("ollama", [], "", time.time() - start,
                                available=False, error=str(e), frame_id=frame_id)


def _run_agy(topic: str, frame_id: str | None = None) -> DivergenceResult:
    """Antigravity (agy) divergence runner — the live Google/Gemini seat.

    Calls the hardened `agy.sh` adapter (argv mode, --sandbox, NO --model
    override: forcing a model once pushed agy onto an exhaustible quota group
    and produced silent empty output — the original zombie-gate incident).
    Zombie gate: empty output or non-zero exit => available=False.
    """
    start = time.time()
    instruction = _build_framed_prompt(
        topic, frame_id,
        "Output: numbered list of distinct branches (ideas, approaches, angles). "
        "Each branch: one sentence label + one sentence rationale. "
        "Minimum 4 branches. Prioritize surprising, non-obvious angles. "
        "Push past the obvious — the first 3 ideas you'd think of are banned.",
    )
    try:
        result = subprocess.run(
            [os.path.join(_ADAPTERS, "agy.sh"), instruction],
            capture_output=True, text=True, timeout=330,
        )
        raw = result.stdout.strip()
        elapsed = time.time() - start
        if _is_quota_error(raw):
            return DivergenceResult("agy", [], raw, elapsed, available=False,
                                    error="quota_exceeded", frame_id=frame_id)
        if result.returncode != 0 or not raw:
            return DivergenceResult("agy", [], raw, elapsed, available=False,
                                    error=(result.stderr.strip() or "empty_output")[:200],
                                    frame_id=frame_id)
        branches = _parse_branches(raw, "agy", frame_id)
        return DivergenceResult("agy", branches, raw, elapsed, frame_id=frame_id)
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return DivergenceResult("agy", [], "", time.time() - start,
                                available=False, error=str(e), frame_id=frame_id)


def _is_quota_error(text: str) -> bool:
    low = text.lower()
    return any(p in low for p in (
        "quota exceeded", "quota_exceeded", "exhausted your capacity",
        "exhausted your daily quota", "quota.*exceeded", "terminalquotaerror",
        "rate limit", "too many requests",
    ))


def _parse_branches(text: str, source: str, frame_id: str | None = None) -> list[Branch]:
    branches = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        if line[0].isdigit() or line.startswith(("-", "*", "•")):
            content = line.lstrip("0123456789.-*• \t")
            if len(content) > 10:
                branches.append(Branch(
                    content=f"[{source}] {content}",
                    frame_id=frame_id,
                ))
    return branches


def _score_branches(branches: list[Branch], topic: str) -> None:
    """
    Lightweight in-process scoring pass (no extra LLM call).
    Approximates adhd's novelty/coherence scores using heuristics:
      novelty:   inter-branch uniqueness (word overlap with the branch pool)
      coherence: topic word overlap (does the branch address the problem?)
      frame_saturation: how much the branch content resembles the frame prompt

    Mutates branches in place, setting branch.score and branch.low_trust_flag.
    """
    if not branches:
        return

    topic_words = set(topic.lower().split())
    all_words = [set(b.content.lower().split()) for b in branches]

    for i, branch in enumerate(branches):
        words = all_words[i]

        # Novelty: inverse of average word overlap with other branches
        if len(branches) > 1:
            overlaps = [
                len(words & all_words[j]) / max(len(words | all_words[j]), 1)
                for j in range(len(branches)) if j != i
            ]
            novelty = 1.0 - (sum(overlaps) / len(overlaps))
        else:
            novelty = 0.5

        # Coherence: topic word overlap, scaled by branch length (very short = low coherence)
        topic_overlap = len(words & topic_words) / max(len(topic_words), 1)
        length_factor = min(len(words) / 20.0, 1.0)  # 20 words = full length credit
        coherence = min(topic_overlap * 0.6 + length_factor * 0.4, 1.0)

        # Frame saturation: overlap with frame prompt words
        frame_saturation = 0.0
        if branch.frame_id and branch.frame_id in FRAMES:
            frame_words = set(FRAMES[branch.frame_id].lower().split())
            frame_saturation = len(words & frame_words) / max(len(frame_words), 1)

        branch.score = ScoreVector(
            novelty=round(novelty, 3),
            coherence=round(coherence, 3),
            frame_saturation=round(frame_saturation, 3),
        )
        branch.low_trust_flag = coherence < 0.3


def _select_frame(provider: str, used_frames: set[str]) -> str | None:
    """Pick the next unused frame from a provider's affinity list."""
    candidates = FRAME_PROVIDER_AFFINITY.get(provider, [])
    for frame in candidates:
        if frame not in used_frames:
            return frame
    # All affinity frames used — fall back to any unused frame
    for frame in FRAMES:
        if frame not in used_frames:
            return frame
    return None


def diverge(
    topic: str,
    providers: list[str] | None = None,
    use_frames: bool = True,
) -> list[DivergenceResult]:
    """
    Run divergence agents in parallel.

    When use_frames=True (default), each provider gets a cognitive frame from
    its affinity list — amplifying its native bias rather than fighting it.
    Frames are assigned so no two providers share the same frame.

    Returns all results including failures so the coupling function can account
    for missing provider perspectives.
    """
    runners: dict[str, object] = {"agy": _run_agy, "ollama": _run_ollama}
    requested = providers or list(runners.keys())
    active = [p for p in requested if p in runners]

    # Fail LOUD on an all-unknown provider list. Unknown names are dropped
    # silently, so an all-unknown list used to reach ThreadPoolExecutor with
    # max_workers=0 and die on an opaque ValueError. The 2026-07 prune removed
    # the `codex` and `gemini` runners, so `--providers codex` is exactly what
    # muscle memory types — it must say so plainly instead of crashing.
    if not active:
        unknown = ", ".join(requested) or "(empty)"
        raise ValueError(
            f"No known divergence providers in: {unknown}. "
            f"Available: {', '.join(sorted(runners))}. "
            "Note: 'codex' and 'gemini' were removed in the 2026-07 fleet prune "
            "(codex quota-dead, gemini CLI retired)."
        )

    # Assign frames before dispatch so each provider gets a distinct one
    used_frames: set[str] = set()
    frame_assignments: dict[str, str | None] = {}
    if use_frames:
        for provider in active:
            frame = _select_frame(provider, used_frames)
            frame_assignments[provider] = frame
            if frame:
                used_frames.add(frame)
    else:
        frame_assignments = {p: None for p in active}

    results = []
    with ThreadPoolExecutor(max_workers=len(active)) as pool:
        futures = {
            pool.submit(runners[p], topic, frame_assignments[p]): p  # type: ignore[operator]
            for p in active
        }
        for f in as_completed(futures):
            results.append(f.result())

    # Score all collected branches in one pass
    all_branches = [b for r in results for b in r.branches]
    _score_branches(all_branches, topic)

    return results
