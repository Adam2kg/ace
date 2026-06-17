"""
Reads a Claude Code session JSONL, calls Claude Haiku to extract memory-worthy facts,
and writes them into the project's memory/ directory.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import anthropic

from .store import known_names, write_memory

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
    try:
        return json.loads(raw).get("memories", [])
    except json.JSONDecodeError:
        pass
    match = re.search(r'\{.*\}', raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group()).get("memories", [])
        except json.JSONDecodeError:
            pass
    return []


def harvest(
    jsonl_path: Path,
    cwd: str | Path,
    *,
    dry_run: bool = False,
    model: str = "claude-haiku-4-5-20251001",
) -> list[dict]:
    """
    Extract memories from jsonl_path and write them to the memory store for cwd.
    Returns the list of memories (written or would-be-written).
    """
    transcript = _extract_turns(jsonl_path)
    if not transcript.strip():
        return []

    existing = known_names(cwd)

    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=model,
        max_tokens=2048,
        system=_SYSTEM,
        messages=[{"role": "user", "content": f"Extract memories:\n\n{transcript}"}],
    )

    memories = _parse_memories(resp.content[0].text)

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
