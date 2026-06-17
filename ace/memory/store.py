"""
Thin I/O layer over ~/.claude/projects/<slug>/memory/.
"""
from __future__ import annotations

from pathlib import Path


def project_slug(cwd: str | Path) -> str:
    """Encode an absolute path to the Claude project slug format."""
    path = str(Path(cwd).expanduser().resolve())
    return path.replace("/", "-")


def memory_dir(cwd: str | Path) -> Path:
    slug = project_slug(cwd)
    return Path.home() / ".claude" / "projects" / slug / "memory"


def memory_index(cwd: str | Path) -> Path:
    return memory_dir(cwd) / "MEMORY.md"


def known_names(cwd: str | Path) -> set[str]:
    """Return the set of memory names already in MEMORY.md."""
    idx = memory_index(cwd)
    if not idx.exists():
        return set()
    names = set()
    for line in idx.read_text().splitlines():
        # lines look like: - [name](filename) — description
        if line.startswith("- ["):
            start = line.index("[") + 1
            end = line.index("]")
            names.add(line[start:end])
    return names


def write_memory(cwd: str | Path, name: str, type_: str, description: str, body: str) -> Path:
    """Write a memory file and update MEMORY.md. Skips if name already exists."""
    mdir = memory_dir(cwd)
    mdir.mkdir(parents=True, exist_ok=True)

    filename = f"{type_}_{name}.md"
    filepath = mdir / filename

    content = (
        f"---\n"
        f"name: {name}\n"
        f"description: {description}\n"
        f"metadata:\n"
        f"  type: {type_}\n"
        f"---\n\n"
        f"{body}\n"
    )
    filepath.write_text(content)

    idx = memory_index(cwd)
    line = f"- [{name}]({filename}) — {description}"

    if idx.exists():
        text = idx.read_text()
        if filename not in text:
            idx.write_text(text.rstrip() + "\n" + line + "\n")
    else:
        idx.write_text(f"# Memory Index\n\n{line}\n")

    return filepath
