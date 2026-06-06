"""
ace — Asymmetric Cognitive Equilibrium Engine
CLI entry point.

Usage:
    ace run <topic>                    # single ACE cycle
    ace run <topic> --cycles 3        # N diverge→synthesize cycles
    ace run <topic> --providers codex,gemini
    ace status                         # show coupling state (requires --state-file)
    ace debt --state-file ace_state.json  # show attractor debt
"""

import json
import sys

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ace.agents.divergence import diverge
from ace.agents.synthesis import TrajectorySegment, synthesize
from ace.coupling.function import CouplingFunction

console = Console()


@click.group()
def main():
    pass


@main.command()
@click.argument("topic")
@click.option("--cycles", default=1, show_default=True, help="Diverge→synthesize cycles to run")
@click.option("--providers", default="codex,gemini", show_default=True,
              help="Comma-separated list of divergence providers")
@click.option("--state-file", default=None, help="Path to persist coupling state JSON")
@click.option("--budget", default=3, show_default=True, help="Base interrupt budget per cycle")
def run(topic: str, cycles: int, providers: str, state_file: str | None, budget: int):
    """Run an ACE session on TOPIC."""
    provider_list = [p.strip() for p in providers.split(",")]

    console.print(Panel(
        f"[bold cyan]ACE — Asymmetric Cognitive Equilibrium[/bold cyan]\n"
        f"[dim]Topic:[/dim] {topic}\n"
        f"[dim]Providers:[/dim] {' '.join(f'[yellow]{p}[/yellow]' for p in provider_list)} + [blue]synthesis(claude)[/blue]\n"
        f"[dim]Cycles:[/dim] {cycles}",
        border_style="cyan",
    ))

    coupling = CouplingFunction(base_interrupt_budget=budget)
    trajectory: list[TrajectorySegment] = []

    for cycle_n in range(1, cycles + 1):
        console.rule(f"[cyan]Cycle {cycle_n}/{cycles} — Diverge[/cyan]")

        with console.status("[yellow]🔴🟡 Dispatching divergence agents in parallel...[/yellow]"):
            results = diverge(topic, provider_list)

        all_branches = []
        for r in results:
            indicator = "🔴" if r.provider == "codex" else "🟡"
            if not r.available:
                console.print(f"{indicator} [red]{r.provider}[/red]: unavailable ({r.error})")
                continue
            console.print(f"\n{indicator} [bold]{r.provider}[/bold] ({r.elapsed:.1f}s) — {len(r.branches)} branches:")
            for b in r.branches:
                console.print(f"  • {b.content}")
            all_branches.extend(r.branches)

        if not all_branches:
            console.print("[red]No branches from any divergence provider. Check provider availability.[/red]")
            sys.exit(1)

        console.rule(f"[blue]Cycle {cycle_n}/{cycles} — Synthesize[/blue]")

        debt = coupling.attractor_debt()
        if debt:
            debt_table = Table(title="Attractor Debt", show_header=True, header_style="bold magenta")
            debt_table.add_column("Branch", style="dim")
            debt_table.add_column("Debt Score", justify="right")
            for sig, score in list(debt.items())[:5]:
                debt_table.add_row(sig[:60], f"{score:.2f}")
            console.print(debt_table)

        with console.status("[blue]🔵 Synthesis agent processing...[/blue]"):
            result = synthesize(topic, all_branches, coupling, trajectory)

        console.print(f"\n[bold blue]🔵 Trajectory Update:[/bold blue] {result.trajectory_update}")
        console.print(f"[green]✓ Integrated ({len(result.integrated)}):[/green] {', '.join(b.content[:50] for b in result.integrated)}")
        console.print(f"[yellow]⏸ Deferred ({len(result.deferred)}):[/yellow] {', '.join(b.content[:50] for b in result.deferred)}")

        if result.high_debt_surfaced:
            console.print(f"\n[magenta]⚡ Attractor debt surfaced:[/magenta]")
            for s in result.high_debt_surfaced:
                console.print(f"  ↑ {s[:80]}")

        if result.convergence_warning:
            console.print("\n[bold red]⚠ CONVERGENCE WARNING:[/bold red] High agreement rate detected. "
                         "The divergence agent may be captured by the synthesis agent's frame. "
                         "Consider increasing noise or switching divergence providers.")

        trajectory.append(TrajectorySegment(
            content=result.trajectory_update,
            integrated_branches=[b.content for b in result.integrated],
        ))

    # Final state
    console.rule("[cyan]Session Complete[/cyan]")
    state = coupling.handoff_state()
    console.print(f"\n[dim]Coupling state:[/dim] budget={state['interrupt_budget']} | "
                 f"segments_completed={state['trajectory_segments_completed']} | "
                 f"deferred_queue={state['deferred_count']}")

    if state_file:
        with open(state_file, "w") as f:
            json.dump(state, f, indent=2)
        console.print(f"[dim]State saved to {state_file}[/dim]")

    console.print("\n[bold]Final Trajectory:[/bold]")
    for i, seg in enumerate(trajectory, 1):
        console.print(f"  [{i}] {seg.content}")


@main.command()
@click.option("--state-file", required=True, help="Path to coupling state JSON")
def debt(state_file: str):
    """Show attractor debt from a saved coupling state."""
    try:
        with open(state_file) as f:
            state = json.load(f)
    except FileNotFoundError:
        console.print(f"[red]State file not found: {state_file}[/red]")
        sys.exit(1)

    attractor = state.get("attractor_debt", {})
    if not attractor:
        console.print("[green]No attractor debt. Clean state.[/green]")
        return

    table = Table(title="Attractor Debt", show_header=True, header_style="bold magenta")
    table.add_column("Branch Signature", style="dim")
    table.add_column("Debt Score", justify="right")
    table.add_column("Status", justify="center")
    for sig, score in attractor.items():
        status = "[red]HIGH[/red]" if score >= 2.5 else "[yellow]MED[/yellow]"
        table.add_row(sig[:70], f"{score:.2f}", status)

    console.print(table)
    if state.get("high_debt_branches"):
        console.print("\n[magenta]High-debt branches needing re-examination:[/magenta]")
        for b in state["high_debt_branches"]:
            console.print(f"  ↑ {b[:100]}")
