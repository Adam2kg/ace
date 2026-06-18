"""
Reads a Claude Code session JSONL, asks an LLM to extract memory-worthy facts,
and writes them into the project's memory/ directory.

Two backends:
  - "ollama" (default): fully local, keyless. Nothing leaves the machine.
  - "haiku": Claude Haiku via the Anthropic API. Higher quality, costs ~a fraction
    of a cent per session, and sends the transcript to Anthropic. Requires
    ANTHROPIC_API_KEY.
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from pathlib import Path

from .store import known_names, write_memory

OLLAMA_URL = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL = "qwen2.5-coder:7b"
DEFAULT_HAIKU_MODEL = "claude-haiku-4-5-20251001"

_SYSTEM = """\
You extract durable memory facts from AI coding assistant session transcripts.

Return ONLY a JSON object — no prose, no markdown fences:
{"memories": [{"name": "kebab-slug", "type": "user|feedback|project|reference", "description": "one-line hook under 150 chars", "body": "markdown body"}]}

Types:
- user: who the user is, their role, expertise, preferences
- feedback: guidance about how to approach work — corrections OR confirmed non-obvious approaches. Lead with the rule, then "**Why:** ..." and "**How to apply:** ..."
- project: non-obvious decisions, constraints, goals for a specific project. Lead with the fact, then "**Why:** ..." and "**How to apply:** ..."
- reference: pointers to external resources (tools, repos, docs, APIs) and their purpose

Rules:
- Only extract facts useful in FUTURE sessions, not just this one
- Skip ephemeral state, in-progress work, debugging steps, things obvious from code
- Quality over quantity — 0 to 5 memories per session
- name: unique kebab-slug, max 40 chars, no spaces
- If nothing is worth keeping, return {"memories": []}\
"""


class OllamaUnavailable(RuntimeError):
    """Raised when the local Ollama server can't be reached."""


def _extract_turns(jsonl_path: Path, max_chars: int = 50_000) -> str:
    turns: list[str] = []
    with open(jsonl_path, encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            if obj.get("isSidechain"):
                continue

            t = obj.get("type")
            if t == "user":
                content = obj.get("message", {}).get("content", "")
                if isinstance(content, str) and content.strip():
                    turns.append(f"USER: {content.strip()}")
            elif t == "assistant":
                for block in obj.get("message", {}).get("content", []):
                    if isinstance(block, dict) and block.get("type") == "text":
                        text = block.get("text", "").strip()
                        if text:
                            turns.append(f"ASSISTANT: {text[:600]}")
                        break

    transcript = "\n\n".join(turns)
    if len(transcript) > max_chars:
        # Keep head + tail — the interesting decisions often come near the end
        half = max_chars // 2
        transcript = transcript[:half] + "\n\n[...MIDDLE TRUNCATED...]\n\n" + transcript[-half:]
    return transcript


def _parse_memories(raw: str) -> list[dict]:
    raw = raw.strip()
    # Strip <think>...</think> blocks that some local models emit
    raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
    try:
        return json.loads(raw).get("memories", [])
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group()).get("memories", [])
        except json.JSONDecodeError:
            pass
    return []


def _ollama_running() -> bool:
    try:
        req = urllib.request.Request(f"{OLLAMA_URL}/api/tags")
        with urllib.request.urlopen(req, timeout=3):
            return True
    except (urllib.error.URLError, OSError):
        return False


def _call_ollama(system: str, user: str, model: str) -> str:
    """Call a local Ollama model with JSON-constrained output."""
    if not _ollama_running():
        raise OllamaUnavailable(
            "Ollama server is not reachable at localhost:11434. Start it with `ollama serve`."
        )

    payload = json.dumps({
        "model": model,
        "format": "json",  # constrain output to valid JSON
        "stream": False,
        "options": {"temperature": 0.2},
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    # Local 7B model on a long transcript — give it room.
    with urllib.request.urlopen(req, timeout=300) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return body.get("message", {}).get("content", "")


def _call_haiku(system: str, user: str, model: str) -> str:
    """Call Claude Haiku via the Anthropic API. Imports anthropic lazily."""
    import anthropic  # noqa: PLC0415 — optional dependency, only needed for this backend

    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=model,
        max_tokens=2048,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return resp.content[0].text


def harvest(
    jsonl_path: Path,
    cwd: str | Path,
    *,
    backend: str = "ollama",
    model: str | None = None,
    dry_run: bool = False,
) -> list[dict]:
    """
    Extract memories from jsonl_path and write them to the memory store for cwd.
    Returns the list of memories (written or would-be-written).

    backend: "ollama" (local, keyless) or "haiku" (Anthropic API).
    """
    transcript = _extract_turns(jsonl_path)
    if not transcript.strip():
        return []

    existing = known_names(cwd)
    user_prompt = f"Extract memories:\n\n{transcript}"

    if backend == "ollama":
        raw = _call_ollama(_SYSTEM, user_prompt, model or DEFAULT_OLLAMA_MODEL)
    elif backend == "haiku":
        raw = _call_haiku(_SYSTEM, user_prompt, model or DEFAULT_HAIKU_MODEL)
    else:
        raise ValueError(f"Unknown backend: {backend!r} (expected 'ollama' or 'haiku')")

    memories = _parse_memories(raw)

    written: list[dict] = []
    for m in memories:
        name = m.get("name", "").strip()
        type_ = m.get("type", "project").strip()
        description = m.get("description", "").strip()
        body = m.get("body", "").strip()

        if not name or not description:
            continue
        if name in existing:
            m["_skipped"] = "already exists"
            written.append(m)
            continue
        if type_ not in {"user", "feedback", "project", "reference"}:
            type_ = "project"

        if not dry_run:
            write_memory(cwd, name, type_, description, body)
            existing.add(name)

        written.append(m)

    return written
