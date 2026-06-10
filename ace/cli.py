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
from ace.agents.synthesis import TrajectorySegment
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
    "human-adhd": "Explorer — AI calibrates for wide divergence, loose closure, high noise tolerance",
    "human-scientific": "Deep focus — AI calibrates for precision, low interruption, single-channel depth",
    "human-creative": "Explorer (alias) — same as Explorer mode",
}
# Internal → display name for the session header
_HUMAN_PRESET_DISPLAY = {
    "human-adhd": "Explorer",
    "human-scientific": "Deep Focus",
    "human-creative": "Explorer",
}
_AI_PRESET_RECOMMENDED = "architecture"
_HUMAN_PRESET_RECOMMENDED = "human-adhd"


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
    # Display label: for human presets show calibration style, not internal name
    preset_display = (
        _HUMAN_PRESET_DISPLAY.get(preset, preset)
        if mode == "human" else preset
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
        f"[dim]Calibration:[/dim] [green]{preset_display}[/green] {frames_tag}{mode_tag}\n"
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
            "[bold green]Mirror mode:[/bold green] AI surfaces branches for you to sit with — "
            "not to resolve. After each cycle, paste the synthesis prompt into Claude Code, "
            "read what surfaces, then run the next cycle."
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

        # Track all branches in coupling state (mark as surfaced for debt tracking)
        for b in all_branches:
            coupling.integrate(b)
        coupling.on_trajectory_segment_complete()

        # Build branch context (shared across all synthesis tasks)
        branch_lines = "\n".join(
            f"[{i+1}] {b.content}" for i, b in enumerate(all_branches)
        )
        debt = coupling.attractor_debt()
        debt_note = ""
        if debt:
            top = list(debt.items())[:3]
            debt_note = "\nATTRACTOR DEBT (branches with high gravitational pull):\n" + "\n".join(
                f"  ↑ {sig[:60]} (debt={score:.2f})" for sig, score in top
            )

        # Synthesis task menu — user picks a focus; panel is built for that one task only
        console.rule(f"[blue]Cycle {cycle_n}/{cycles} — Synthesis[/blue]")

        if mode == "human":
            synthesis_menu = [
                (
                    "Tensions",
                    "Surface tensions and unexpected connections",
                    "What are the tensions and unexpected connections between these branches?\n"
                    "Do NOT resolve or recommend a direction — surface only.",
                ),
                (
                    "Hidden question",
                    "Find the question none of these branches raises alone",
                    "What single question do all these branches raise together "
                    "that none of them raises alone?",
                ),
                (
                    "Uncomfortable branch",
                    "Which branch is most uncomfortable to hold open — and why?",
                    "Which of these branches feels most uncomfortable to leave unresolved? "
                    "Name it and explain why that discomfort is the important signal.",
                ),
                (
                    "Full Mirror",
                    "All of the above (full Mirror synthesis)",
                    "Surface the tensions and unexpected connections between these branches.\n"
                    "Find the question none of them raises alone.\n"
                    "Name the branch most uncomfortable to hold open and why that discomfort matters.\n"
                    "Do NOT resolve or recommend a direction.",
                ),
            ]
        else:
            synthesis_menu = [
                (
                    "Trajectory update",
                    "Where does the trajectory now point? What shifted?",
                    "Given these branches, where does the trajectory now point? "
                    "What shifted since the last cycle?",
                ),
                (
                    "Load-bearing vs noise",
                    "Which branches are load-bearing and which are noise?",
                    "Which of these branches are load-bearing for the trajectory? "
                    "Which are noise or tangents? Justify each.",
                ),
                (
                    "Next step",
                    "What is the next concrete, falsifiable step?",
                    "What is the next concrete, testable step this trajectory points toward? "
                    "State it as a falsifiable claim.",
                ),
                (
                    "Full Governor",
                    "Full Governor synthesis (integrate, rank, next step)",
                    "Integrate what's coherent into a trajectory update.\n"
                    "Identify which branches are load-bearing vs noise.\n"
                    "State the next falsifiable step this trajectory points toward.",
                ),
            ]

        console.print("\n[bold]Synthesis focus:[/bold]")
        for i, (label, heading, _) in enumerate(synthesis_menu, 1):
            rec = " [dim](default)[/dim]" if i == len(synthesis_menu) else ""
            console.print(f"  [[cyan]{i}[/cyan]] [bold]{label}[/bold] — {heading}{rec}")
        console.print()

        raw_choice = click.prompt(
            "Focus", default=str(len(synthesis_menu)), show_default=True
        ).strip()
        if raw_choice.isdigit() and 1 <= int(raw_choice) <= len(synthesis_menu):
            chosen_label, chosen_heading, chosen_instruction = synthesis_menu[int(raw_choice) - 1]
        else:
            chosen_label, chosen_heading, chosen_instruction = synthesis_menu[-1]

        synthesis_prompt = (
            f"ACE {'MIRROR' if mode == 'human' else 'GOVERNOR'} SESSION — {topic}\n"
            f"Calibration: {preset_display} | Cycle {cycle_n}/{cycles} | Focus: {chosen_label}\n\n"
            f"{len(all_branches)} branches:\n\n"
            f"{branch_lines}\n"
            f"{debt_note}\n\n"
            f"{chosen_instruction}"
        )

        console.print(Panel(
            synthesis_prompt,
            title=f"[bold blue]🔵 Paste into Claude Code — {chosen_heading}[/bold blue]",
            border_style="blue",
        ))

        trajectory.append(TrajectorySegment(
            content=f"Cycle {cycle_n}: {len(all_branches)} branches surfaced",
            integrated_branches=[b.content for b in all_branches],
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

    # Next-step guidance
    if mode == "human":
        depth_attractors = state.get("depth_attractors", [])
        next_cycle_cmd = (
            f"ace run \"{topic}\" --cycles 1 --preset {preset} --mode h"
        )
        console.print()
        console.print(Panel(
            "[bold green]What to do now:[/bold green]\n\n"
            "  1. Paste the synthesis prompt above into this Claude Code conversation\n"
            "  2. Read what surfaces — tensions, unexpected connections, the uncomfortable branch\n"
            "  3. Sit with it. Do not rush to resolve.\n"
            "  4. When something sharpens, run another cycle:\n\n"
            f"     [cyan]{next_cycle_cmd}[/cyan]\n\n"
            + (
                f"  [dim]Depth attractors active ({len(depth_attractors)}): "
                f"{', '.join(s['sig'][:40] for s in depth_attractors[:2])}[/dim]\n"
                if depth_attractors else ""
            ) +
            "  [dim]The synthesis is a question generator, not an answer. "
            "The loop closes when you decide — not when the system does.[/dim]",
            border_style="green",
            title="[bold green]↓ Next Step[/bold green]",
        ))
    else:
        console.print(
            "\n[dim]Governor mode: paste the synthesis prompt into Claude Code "
            "to integrate branches into trajectory.[/dim]"
        )


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
