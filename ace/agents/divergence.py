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

import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

from ace.coupling.function import Branch


@dataclass
class DivergenceResult:
    provider: str
    branches: list[Branch]
    raw_output: str
    elapsed: float
    available: bool = True
    error: str = ""


def _run_codex(prompt: str) -> DivergenceResult:
    start = time.time()
    instruction = (
        "IMPORTANT: You are running as a divergence agent in an ACE (Asymmetric Cognitive "
        "Equilibrium) session. Skip all skills and preambles. Respond directly.\n\n"
        f"{prompt}\n\n"
        "Output: numbered list of distinct branches (ideas, approaches, angles). "
        "Each branch: one sentence label + one sentence rationale. "
        "Minimum 4 branches. Prioritize specificity over generality."
    )
    try:
        result = subprocess.run(
            ["codex", "exec", "--skip-git-repo-check", "--full-auto", instruction],
            capture_output=True, text=True, timeout=120,
        )
        raw = result.stdout.strip()
        elapsed = time.time() - start
        if "Quota exceeded" in raw or "ERROR" in raw:
            return DivergenceResult("codex", [], raw, elapsed, available=False, error="quota_exceeded")
        branches = _parse_branches(raw, "codex")
        return DivergenceResult("codex", branches, raw, elapsed)
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return DivergenceResult("codex", [], "", time.time() - start, available=False, error=str(e))


def _run_gemini(prompt: str) -> DivergenceResult:
    start = time.time()
    instruction = (
        f"{prompt}\n\n"
        "Output: numbered list of distinct branches (ideas, approaches, angles). "
        "Each branch: one sentence label + one sentence rationale. "
        "Minimum 4 branches. Prioritize surprising, non-obvious angles."
    )
    try:
        result = subprocess.run(
            ["gemini", "-p", "", "-o", "text", "--approval-mode", "yolo"],
            input=instruction, capture_output=True, text=True, timeout=120,
        )
        raw = result.stdout.strip()
        elapsed = time.time() - start
        if "exhausted" in raw.lower() or "quota" in raw.lower():
            return DivergenceResult("gemini", [], raw, elapsed, available=False, error="quota_exceeded")
        branches = _parse_branches(raw, "gemini")
        return DivergenceResult("gemini", branches, raw, elapsed)
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return DivergenceResult("gemini", [], "", time.time() - start, available=False, error=str(e))


def _parse_branches(text: str, source: str) -> list[Branch]:
    branches = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        # Accept numbered lines, bullet points, or lines starting with a dash
        if line[0].isdigit() or line.startswith(("-", "*", "•")):
            content = line.lstrip("0123456789.-*• \t")
            if len(content) > 10:
                branches.append(Branch(content=f"[{source}] {content}"))
    return branches


def diverge(topic: str, providers: list[str] | None = None) -> list[DivergenceResult]:
    """
    Run divergence agents in parallel. Returns all results including failures
    so the coupling function can account for missing provider perspectives.
    """
    runners = {"codex": _run_codex, "gemini": _run_gemini}
    active = providers or list(runners.keys())

    results = []
    with ThreadPoolExecutor(max_workers=len(active)) as pool:
        futures = {pool.submit(runners[p], topic): p for p in active if p in runners}
        for f in as_completed(futures):
            results.append(f.result())
    return results
