"""
Synthesis agent — Autism-mode.

Maps onto Claude in the Octopus provider model (🔵).

Responsibilities:
  - Trajectory maintenance: where is the reasoning going and why
  - Branch integration: decide which divergence branches to absorb
  - Attractor debt surface: when deferred branches hit threshold, re-examine
  - Convergence detection: flag if ADHD agent has been captured

The synthesis agent is a compression function, not a filter.
Timing matters: the same branch means something different depending on
when in the trajectory it arrives. A branch during divergent-peak =
candidate. Same branch during consolidation = confirming signal.

Memory warning: relational_context from the coupling function is NOT
portable to a different synthesis agent. If you swap agents mid-session,
coupling history is lost.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import anthropic

from ace.coupling.function import Branch, CouplingFunction, ReceptivityState


@dataclass
class TrajectorySegment:
    content: str
    integrated_branches: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


@dataclass
class SynthesisResult:
    trajectory_update: str
    integrated: list[Branch]
    deferred: list[Branch]
    high_debt_surfaced: list[str]
    convergence_warning: bool
    elapsed: float


def synthesize(
    topic: str,
    branches: list[Branch],
    coupling: CouplingFunction,
    trajectory_history: list[TrajectorySegment],
    mode: str = "ai",
    model: str = "claude-sonnet-4-6",
) -> SynthesisResult:
    """
    Run the synthesis agent (Claude) to integrate divergence branches into
    the current trajectory.

    The coupling function governs which branches are presented and tracks
    what gets deferred for attractor debt calculation.

    mode="ai"    (Governor): compression function — integrate what's coherent, defer the rest.
                 Parser default: DEFERRED. Branches must be explicitly integrated.
    mode="human" (Mirror):   surface function — reflect tensions back to human, don't resolve.
                 Parser default: INTEGRATED. Branches surface by default; only defer contradictions.
    """
    start = time.time()

    coupling.set_receptivity(ReceptivityState.CONSOLIDATING)

    high_debt = coupling.high_debt_branches()
    attractor_debt_report = ""
    if high_debt:
        attractor_debt_report = (
            "\n\nATTRACTOR DEBT ALERT — these branches have been deferred multiple times "
            "and are exerting gravitational pull on the trajectory. Re-examine before proceeding:\n"
            + "\n".join(f"  - {b.content}" for b in high_debt)
        )

    trajectory_summary = ""
    if trajectory_history:
        trajectory_summary = "\n\nTRAJECTORY SO FAR:\n" + "\n".join(
            f"  [{i+1}] {seg.content[:120]}"
            for i, seg in enumerate(trajectory_history[-5:])
        )

    if mode == "human":
        role_instruction = (
            "You are the synthesis agent in an ACE MIRROR session (human thinking scaffold).\n"
            "Your role: surface and reflect — NOT compress or resolve.\n"
            "The human is doing the thinking. Your job is to make the space visible, not to close it.\n\n"
            "Instructions:\n"
            "- Integrate ALL branches as live surfaces — present them as tensions or open questions\n"
            "- DEFER only branches that directly contradict each other and cannot coexist as open questions\n"
            "- TRAJECTORY_UPDATE: describe tensions, unexpected connections, and the core question raised.\n"
            "  Do NOT recommend a direction. Do NOT resolve. Surface the thinking space for the human.\n"
            "- CONVERGENCE_WARNING: YES if everything points to one answer (premature closure risk)"
        )
    else:
        role_instruction = (
            "You are the synthesis agent in an ACE (Asymmetric Cognitive Equilibrium) session.\n"
            "Your role: compression function, not filter. Maintain trajectory. Integrate what's coherent.\n"
            "Defer what isn't — but record WHY, because deferred branches accumulate attractor debt."
        )

    prompt = f"""{role_instruction}

Topic: {topic}
{trajectory_summary}
{attractor_debt_report}

INCOMING BRANCHES (from divergence agents):
{chr(10).join(f"  [{i+1}] {b.content}" for i, b in enumerate(branches))}

Respond in this exact format:
TRAJECTORY_UPDATE: <one paragraph — where the trajectory now points and what shifted>
INTEGRATED: <comma-separated branch numbers you are absorbing into the trajectory>
DEFERRED: <comma-separated branch numbers you are deferring, with brief reason each>
CONVERGENCE_WARNING: <YES if you notice you're agreeing with everything, NO otherwise>"""

    try:
        client = anthropic.Anthropic()
        message = client.messages.create(
            model=model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()
    except anthropic.AuthenticationError:
        raw = "[synthesis-error] ANTHROPIC_API_KEY missing or invalid"
    except anthropic.APIError as e:
        raw = f"[synthesis-error] API error: {e}"
    except Exception as e:
        raw = f"[synthesis-error] {e}"

    integrated, deferred = _parse_synthesis_response(raw, branches, mode=mode)

    for b in integrated:
        coupling.integrate(b)
    for b in deferred:
        coupling.defer(b)

    coupling.on_trajectory_segment_complete()
    coupling.set_receptivity(ReceptivityState.OPEN)

    agreement_rate = len(integrated) / max(len(branches), 1)
    convergence_warn = coupling.convergence_warning(agreement_rate)

    trajectory_update = _extract_section(raw, "TRAJECTORY_UPDATE")
    if not trajectory_update:
        if raw.startswith("[synthesis-error]"):
            trajectory_update = raw  # surface the error
        elif mode == "human":
            # Mirror fallback: name the branches without framing them
            trajectory_update = (
                f"{len(integrated)} surfaces opened: "
                + " | ".join(b.content[:60] for b in integrated[:3])
                + (" | ..." if len(integrated) > 3 else "")
            )
        else:
            trajectory_update = "(synthesis agent returned no update)"

    elapsed = time.time() - start
    return SynthesisResult(
        trajectory_update=trajectory_update,
        integrated=integrated,
        deferred=deferred,
        high_debt_surfaced=[b.content for b in high_debt],
        convergence_warning=convergence_warn,
        elapsed=elapsed,
    )


def _parse_synthesis_response(
    raw: str, branches: list[Branch], mode: str = "ai",
) -> tuple[list[Branch], list[Branch]]:
    integrated_nums: set[int] = set()
    deferred_nums: set[int] = set()

    for line in raw.split("\n"):
        if line.startswith("INTEGRATED:"):
            nums = _extract_numbers(line)
            integrated_nums.update(nums)
        elif line.startswith("DEFERRED:"):
            nums = _extract_numbers(line)
            deferred_nums.update(nums)

    if mode == "human":
        # Mirror mode: default is INTEGRATED — surfaces appear by default.
        # Only branches explicitly named in DEFERRED are held back.
        explicitly_deferred = set(deferred_nums)
        integrated = [b for i, b in enumerate(branches, 1) if i not in explicitly_deferred]
        deferred = [b for i, b in enumerate(branches, 1) if i in explicitly_deferred]
    else:
        # Governor mode: default is DEFERRED — branches must earn integration.
        # Anything not explicitly integrated stays in the deferral queue.
        integrated = [b for i, b in enumerate(branches, 1) if i in integrated_nums]
        deferred = [b for i, b in enumerate(branches, 1) if i in deferred_nums or i not in integrated_nums]

    return integrated, deferred


def _extract_numbers(text: str) -> list[int]:
    import re
    return [int(n) for n in re.findall(r"\d+", text)]


def _extract_section(text: str, key: str) -> str:
    for line in text.split("\n"):
        if line.startswith(f"{key}:"):
            return line[len(key) + 1:].strip()
    return ""
