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

from __future__ import annotations

import json
import sys

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ace.agents.divergence import diverge
from ace.agents.synthesis import TrajectorySegment, synthesize
from ace.coupling.function import CouplingFunction
from ace.presets import PRESETS, apply_human_mode, apply_overrides, effective_synthesis_strength, get_preset

console = Console()


@click.group()
def main():
    pass


_PRESET_LABELS = {
    "architecture": "Architecture — Sonnet→Opus (synthesis-heavy, debate winner for creative work)",
    "debugging": "Debugging — Sonnet→Opus (follow hypothesis deep, low noise)",
    "design-review": "Design review — Haiku→Sonnet (fast variation, consistency tracking)",
    "looping": "Looping — Haiku→Sonnet (throughput mode)",
}
_PRESET_RECOMMENDED = "architecture"


@main.command()
@click.argument("topic")
@click.option("--cycles", default=1, show_default=True, help="Diverge→synthesize cycles to run")
@click.option("--providers", default="codex,gemini", show_default=True,
              help="Comma-separated list of divergence providers")
@click.option("--state-file", default=None, help="Path to persist coupling state JSON")
@click.option("--preset", default=None, type=click.Choice(list(PRESETS.keys())),
              help="Coupling preset. Omit to get an interactive recommendation.")
@click.option("--human-mode", is_flag=True, default=False,
              help="Human is actively contributing divergence — AI divergence becomes amplifier")
@click.option("--synthesis-strength", default=None, type=float,
              help="Override synthesis strength (1.0–5.0)")
@click.option("--divergence-model", default=None, help="Override divergence model")
@click.option("--synthesis-model", default=None, help="Override synthesis model")
@click.option("--budget", default=None, type=int,
              help="Override base interrupt budget (preset default used if omitted)")
@click.option("--debt-threshold", default=None, type=float,
              help="Override attractor debt surface threshold")
def run(
    topic: str, cycles: int, providers: str, state_file: str | None,
    preset: str | None, human_mode: bool,
    synthesis_strength: float | None, divergence_model: str | None,
    synthesis_model: str | None, budget: int | None, debt_threshold: float | None,
):
    """Run an ACE session on TOPIC."""
    provider_list = [p.strip() for p in providers.split(",")]

    # Interactive preset selection when not given explicitly
    if preset is None:
        console.print("\n[bold cyan]ACE — Select coupling preset[/bold cyan]")
        console.print("[dim]Recommendations from 3-round multi-provider debate:[/dim]\n")
        choices = list(PRESETS.keys())
        for i, key in enumerate(choices, 1):
            rec = " [green](recommended — debate winner)[/green]" if key == _PRESET_RECOMMENDED else ""
            console.print(f"  [{i}] {_PRESET_LABELS[key]}{rec}")
        console.print()
        raw = click.prompt(
            "Preset",
            default="1",
            show_default=True,
        ).strip()
        # Accept number or name
        if raw.isdigit() and 1 <= int(raw) <= len(choices):
            preset = choices[int(raw) - 1]
        elif raw in choices:
            preset = raw
        else:
            console.print(f"[red]Unknown selection '{raw}', defaulting to {_PRESET_RECOMMENDED}[/red]")
            preset = _PRESET_RECOMMENDED

        if not human_mode:
            human_mode = click.confirm(
                "Are you actively contributing ideas? (human-mode: AI divergence becomes amplifier)",
                default=False,
            )

    profile = get_preset(preset)
    if human_mode:
        profile = apply_human_mode(profile)
    profile = apply_overrides(
        profile,
        synthesis_strength=synthesis_strength,
        divergence_model=divergence_model,
        synthesis_model=synthesis_model,
        budget=budget,
        debt_threshold=debt_threshold,
    )

    mode_tag = "[magenta]human-mode[/magenta] " if human_mode else ""
    console.print(Panel(
        f"[bold cyan]ACE — Asymmetric Cognitive Equilibrium[/bold cyan]\n"
        f"[dim]Topic:[/dim] {topic}\n"
        f"[dim]Preset:[/dim] [green]{preset}[/green] {mode_tag}\n"
        f"[dim]Divergence:[/dim] [yellow]{profile.divergence_model}[/yellow] ({', '.join(provider_list)})\n"
        f"[dim]Synthesis:[/dim] [blue]{profile.synthesis_model}[/blue] "
        f"(strength {profile.synthesis_strength}/5{'↗' if profile.dynamic_cq else ''})\n"
        f"[dim]Cycles:[/dim] {cycles} | "
        f"[dim]Debt threshold:[/dim] {profile.debt_surface_threshold} | "
        f"[dim]Budget:[/dim] {profile.base_interrupt_budget}",
        border_style="cyan",
    ))
    if human_mode:
        console.print(
            "[magenta]Human mode:[/magenta] You are the primary divergence engine. "
            "AI divergence amplifies and finds edge cases. Convergence warnings suppressed."
        )

    coupling = CouplingFunction(
        base_interrupt_budget=profile.base_interrupt_budget,
        receptivity_noise_sigma=profile.receptivity_noise_sigma,
        debt_surface_threshold=profile.debt_surface_threshold,
    )
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

        if result.convergence_warning and profile.convergence_warning_enabled:
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
