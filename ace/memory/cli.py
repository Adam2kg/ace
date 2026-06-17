"""ace memory — harvest and inspect session memories."""
from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from .harvester import harvest
from .store import memory_dir, memory_index, project_slug

console = Console()


def _latest_jsonl(cwd: Path) -> Path | None:
    slug = project_slug(cwd)
    project_dir = Path.home() / ".claude" / "projects" / slug
    jsonls = sorted(project_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    return jsonls[0] if jsonls else None


@click.group("memory")
def memory_group():
    """Personal memory engine — harvest session memories and inspect the store."""
    pass


@memory_group.command("harvest")
@click.option("--session", "-s", type=click.Path(exists=True), help="Path to session JSONL (default: latest)")
@click.option("--cwd", "-C", default=".", show_default=True, help="Project directory")
@click.option("--dry-run", is_flag=True, help="Show what would be written, don't write")
def cmd_harvest(session, cwd, dry_run):
    """Extract memories from the latest (or a specific) session transcript."""
    cwd = Path(cwd).resolve()

    if session:
        jsonl = Path(session)
    else:
        jsonl = _latest_jsonl(cwd)
        if not jsonl:
            console.print(f"[red]No session transcripts found for {cwd}[/red]")
            sys.exit(1)
        console.print(f"Latest session: [dim]{jsonl.name}[/dim]")

    console.print(f"Harvesting [cyan]{jsonl.name}[/cyan] …")

    memories = harvest(jsonl, cwd, dry_run=dry_run)

    if not memories:
        console.print("[dim]Nothing worth keeping extracted.[/dim]")
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("Type", style="cyan", width=12)
    table.add_column("Name", style="bold", width=32)
    table.add_column("Description")

    for m in memories:
        suffix = " [dim](skipped — exists)[/dim]" if m.get("_skipped") else ""
        table.add_row(m.get("type", "?"), m.get("name", "?"), m.get("description", "") + suffix)

    console.print(table)

    if dry_run:
        console.print("[yellow]Dry run — nothing written.[/yellow]")
    else:
        new = [m for m in memories if not m.get("_skipped")]
        if new:
            console.print(f"[green]Wrote {len(new)} memories to {memory_dir(cwd)}[/green]")


@memory_group.command("backfill")
@click.option("--cwd", "-C", default=".", show_default=True, help="Project directory")
@click.option("--limit", "-n", default=5, show_default=True, help="Max sessions to process")
@click.option("--dry-run", is_flag=True)
def cmd_backfill(cwd, limit, dry_run):
    """Harvest memories from the N most recent past sessions."""
    cwd = Path(cwd).resolve()
    slug = project_slug(cwd)
    project_dir = Path.home() / ".claude" / "projects" / slug
    jsonls = sorted(project_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)

    if not jsonls:
        console.print("[red]No session transcripts found.[/red]")
        return

    total_new = 0
    for jsonl in jsonls[:limit]:
        console.print(f"[dim]{jsonl.name}[/dim] …")
        memories = harvest(jsonl, cwd, dry_run=dry_run)
        new = [m for m in memories if not m.get("_skipped")]
        total_new += len(new)
        for m in new:
            console.print(f"  [cyan]{m['type']}[/cyan]  {m['name']}: {m['description']}")

    label = "Would write" if dry_run else "Wrote"
    console.print(f"\n[green]{label} {total_new} memories from {min(limit, len(jsonls))} sessions.[/green]")


@memory_group.command("show")
@click.option("--cwd", "-C", default=".", show_default=True, help="Project directory")
def cmd_show(cwd):
    """Print the memory index for the current project."""
    cwd = Path(cwd).resolve()
    idx = memory_index(cwd)
    if not idx.exists():
        console.print("[dim]No memory index found.[/dim]")
        return
    console.print(idx.read_text())
