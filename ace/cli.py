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
from ace.presets import DEFAULT_HUMAN_PRESET, PRESETS, apply_human_mode, apply_overrides, effective_synthesis_strength, get_preset

console = Console()


@click.group()
def main():
    pass


_AI_PRESET_LABELS = {
    "architecture": "Architecture — Sonnet→Opus (synthesis-heavy, debate winner for creative work)",
    "debugging": "Debugging — Sonnet→Opus (follow hypothesis deep, low noise)",
    "design-review": "Design review — Haiku→Sonnet (fast variation, consistency tracking)",
    "looping": "Looping — Haiku→Sonnet (throughput mode)",
    "frames-deep": "Frames-deep — Sonnet→Sonnet, single provider (conceptual / budget-constrained / quota fallback)",
    "frames-adversarial": "Frames-adversarial — Sonnet→Opus, single provider (security / regulated / threat modeling)",
}
_HUMAN_PRESET_LABELS = {
    "human-scientific": "Scientific/architectural — Mirror mode, surface attractors fast, warn on premature closure",
    "human-creative": "Creative/narrative — Mirror mode, wide divergence window, no convergence pressure",
}
_AI_PRESET_RECOMMENDED = "architecture"
_HUMAN_PRESET_RECOMMENDED = "human-scientific"


@main.command()
@click.argument("topic")
@click.option("--cycles", default=1, show_default=True, help="Diverge→synthesize cycles to run")
@click.option("--providers", default="codex,gemini", show_default=True,
              help="Comma-separated list of divergence providers")
@click.option("--state-file", default=None, help="Path to persist coupling state JSON")
@click.option("--preset", default=None, type=click.Choice(list(PRESETS.keys())),
              help="Coupling preset (power-user: skips mode question, implies --mode a for ai presets).")
@click.option("--mode", default=None, type=click.Choice(["h", "a", "human", "ai"]),
              help="Root mode: h/human (I need to think) or a/ai (my AI needs to think). "
                   "Omit to get the mode question.")
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
    preset: str | None, mode: str | None, human_mode: bool,
    synthesis_strength: float | None, divergence_model: str | None,
    synthesis_model: str | None, budget: int | None, debt_threshold: float | None,
):
    """Run an ACE session on TOPIC."""
    provider_list = [p.strip() for p in providers.split(",")]

    # Normalize mode flag
    if mode in ("h", "human"):
        mode = "human"
    elif mode in ("a", "ai"):
        mode = "ai"

    # --preset implies ai-mode for all existing ai presets; human presets set mode automatically
    if preset is not None and mode is None:
        preset_obj = PRESETS.get(preset)
        if preset_obj:
            mode = preset_obj.mode  # read from preset definition

    # Root mode declaration — one question, not skippable unless --mode or --preset given
    if mode is None:
        console.print("\n[bold cyan]ACE — How would you like to think?[/bold cyan]\n")
        console.print("  [H] I need to think through something   [dim](human-mode: Mirror)[/dim]")
        console.print("  [A] My AI needs to think through this   [dim](ai-mode: Governor)[/dim]")
        console.print()
        raw = click.prompt("Mode", default="H").strip().upper()
        mode = "human" if raw in ("H", "HUMAN", "") else "ai"

    # Select preset — human-mode picks from human presets, ai-mode from ai presets
    if preset is None:
        if mode == "human":
            console.print("\n[bold cyan]ACE — Task type[/bold cyan]\n")
            h_choices = list(_HUMAN_PRESET_LABELS.keys())
            for i, key in enumerate(h_choices, 1):
                rec = " [green](recommended)[/green]" if key == _HUMAN_PRESET_RECOMMENDED else ""
                console.print(f"  [{i}] {_HUMAN_PRESET_LABELS[key]}{rec}")
            console.print()
            raw = click.prompt("Type", default="1", show_default=True).strip()
            if raw.isdigit() and 1 <= int(raw) <= len(h_choices):
                preset = h_choices[int(raw) - 1]
            elif raw in h_choices:
                preset = raw
            else:
                preset = DEFAULT_HUMAN_PRESET
        else:
            console.print("\n[bold cyan]ACE — Select coupling preset[/bold cyan]")
            console.print("[dim]Recommendations from 3-round multi-provider debate:[/dim]\n")
            choices = list(_AI_PRESET_LABELS.keys())
            for i, key in enumerate(choices, 1):
                rec = " [green](recommended — debate winner)[/green]" if key == _AI_PRESET_RECOMMENDED else ""
                console.print(f"  [{i}] {_AI_PRESET_LABELS[key]}{rec}")
            console.print()
            raw = click.prompt("Preset", default="1", show_default=True).strip()
            if raw.isdigit() and 1 <= int(raw) <= len(choices):
                preset = choices[int(raw) - 1]
            elif raw in choices:
                preset = raw
            else:
                preset = _AI_PRESET_RECOMMENDED

        if mode == "ai" and not human_mode:
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

    frames_tag = "[cyan]frames-only[/cyan] " if profile.frames_only else ""
    mode_tag = "[magenta]human-mode[/magenta] " if human_mode else ""
    root_mode_label = (
        "[bold green]MIRROR[/bold green] [dim](human thinking scaffold)[/dim]"
        if mode == "human" else
        "[bold blue]GOVERNOR[/bold blue] [dim](AI thinking scaffold)[/dim]"
    )
    divergence_line = (
        f"[dim]Divergence:[/dim] [yellow]{profile.divergence_model}[/yellow] "
        f"(frames-{profile.frames_set})"
        if profile.frames_only else
        f"[dim]Divergence:[/dim] [yellow]{profile.divergence_model}[/yellow] "
        f"({', '.join(provider_list)}) + cognitive frames"
    )
    console.print(Panel(
        f"[bold cyan]ACE — Asymmetric Cognitive Equilibrium[/bold cyan]\n"
        f"[dim]Mode:[/dim] {root_mode_label}\n"
        f"[dim]Topic:[/dim] {topic}\n"
        f"[dim]Preset:[/dim] [green]{preset}[/green] {frames_tag}{mode_tag}\n"
        f"{divergence_line}\n"
        f"[dim]Synthesis:[/dim] [blue]{profile.synthesis_model}[/blue] "
        f"(strength {profile.synthesis_strength}/5{'↗' if profile.dynamic_cq else ''})\n"
        f"[dim]Cycles:[/dim] {cycles} | "
        f"[dim]Debt threshold:[/dim] {profile.debt_surface_threshold} | "
        f"[dim]Budget:[/dim] {profile.base_interrupt_budget}",
        border_style="cyan" if mode == "ai" else "green",
    ))
    if mode == "human":
        console.print(
            "[bold green]Mirror mode:[/bold green] AI amplifies your thinking. "
            "Synthesis holds back until you have material to work with."
        )
    if human_mode and mode == "ai":
        console.print(
            "[magenta]Human mode:[/magenta] You are the primary divergence engine. "
            "AI divergence amplifies and finds edge cases. Convergence warnings suppressed."
        )
    if profile.frames_only:
        console.print(
            f"[cyan]Frames-only mode:[/cyan] Single provider, cognitive frames "
            f"({profile.frames_set} set). No multi-provider dispatch."
        )

    coupling = CouplingFunction(
        base_interrupt_budget=profile.base_interrupt_budget,
        receptivity_noise_sigma=profile.receptivity_noise_sigma,
        debt_surface_threshold=profile.debt_surface_threshold,
        mode=mode,
    )
    trajectory: list[TrajectorySegment] = []

    for cycle_n in range(1, cycles + 1):
        console.rule(f"[cyan]Cycle {cycle_n}/{cycles} — Diverge[/cyan]")

        dispatch_label = (
            "[cyan]🔵 Running frames-only divergence...[/cyan]"
            if profile.frames_only else
            "[yellow]🔴🟡 Dispatching divergence agents + cognitive frames in parallel...[/yellow]"
        )
        with console.status(dispatch_label):
            results = diverge(topic, provider_list, use_frames=not profile.frames_only)

        all_branches = []
        for r in results:
            indicator = "🔴" if r.provider == "codex" else "🟡"
            if not r.available:
                console.print(f"{indicator} [red]{r.provider}[/red]: unavailable ({r.error})")
                continue
            frame_label = f" [dim][{r.frame_id}][/dim]" if r.frame_id else ""
            console.print(
                f"\n{indicator} [bold]{r.provider}[/bold]{frame_label} "
                f"({r.elapsed:.1f}s) — {len(r.branches)} branches:"
            )
            for b in r.branches:
                trust_marker = " [red][low-trust][/red]" if b.low_trust_flag else ""
                score_str = f" [dim]n={b.score.novelty:.2f} c={b.score.coherence:.2f}[/dim]" if b.score else ""
                console.print(f"  •{trust_marker} {b.content}{score_str}")
            all_branches.extend(r.branches)

        if not all_branches:
            console.print("[red]No branches from any divergence provider. Check provider availability.[/red]")
            sys.exit(1)

        if coupling.frame_monoculture_risk(all_branches):
            console.print(
                "\n[bold yellow]⚠ FRAME MONOCULTURE:[/bold yellow] > 80% of weighted branches "
                "share the same cognitive frame. Frame rotation recommended before next cycle."
            )

        if coupling.overthinking_warning():
            console.print(
                "\n[bold yellow]⚠ OVERTHINKING DETECTED:[/bold yellow] Same attractors "
                "returning after nominal closure (re-emergence debt). "
                "Forcing binary closure — commit or explicitly discard before continuing."
            )

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
            if mode == "human":
                console.print(
                    "\n[bold red]⚠ PREMATURE CLOSURE:[/bold red] High agreement before "
                    "sufficient exploration. You may be locking onto a frame before testing it. "
                    "Consider holding this conclusion open for one more cycle."
                )
            else:
                console.print(
                    "\n[bold red]⚠ CONVERGENCE WARNING:[/bold red] High agreement rate detected. "
                    "The divergence agent may be captured by the synthesis agent's frame. "
                    "Consider increasing noise or switching divergence providers."
                )

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


if __name__ == "__main__":
    main()
