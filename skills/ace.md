# /ace — Asymmetric Cognitive Equilibrium

Run an ACE session: divergence agents (🔴🟡) generate branches in parallel,
the synthesis agent (🔵) integrates via the coupling function.

The coupling function — not the agents — is the primary design object.

## Usage

```
/ace <topic>
/ace <topic> --cycles 3
/ace <topic> --providers codex,gemini
```

## What it does

1. **Diverge** — Codex + Gemini run in parallel, each producing Branch candidates
2. **Couple** — interrupt budget, receptivity signal, and deferral queue regulate interaction
3. **Synthesize** — Claude integrates coherent branches, defers others (building attractor debt)
4. **Report** — coupling state, attractor debt, convergence warnings

## When to use over /octo:brainstorm

- When you want the coupling function layer — tracking *what got deferred*, *attractor debt*, and *convergence warnings*
- When you want persistent trajectory across multiple cycles (`--cycles N`)
- When you want to study the coupling dynamics themselves (save `--state-file` and run `ace debt`)

## Instructions for Claude

When the user invokes `/ace`:

1. Extract the topic from the args
2. Check if `ace` CLI is available: `command -v ace`
3. If available, run: `ace run "<topic>" --cycles 1`
4. Display the output with Octopus provider indicators:
   - 🔴 Codex results
   - 🟡 Gemini results  
   - 🔵 Claude synthesis
5. After the run, check for convergence warnings in the output
6. Ask the user if they want another cycle (`ace run --cycles 1` again with the same state file)

If `ace` CLI is not available, instruct the user to install it:
```bash
cd ~/ace && pip install -e .
```

## Provider indicators (MANDATORY)

Always display before running:
```
🐙 ACE — Asymmetric Cognitive Equilibrium
🔴 Codex: [available/unavailable] — divergence (technical branches)
🟡 Gemini: [available/unavailable] — divergence (lateral branches)
🔵 Claude: available — synthesis (trajectory maintenance)
```

## Key concepts

**Attractor debt** — when the synthesis agent keeps deferring the same class of branch,
debt accumulates. When it exceeds the threshold, ACE surfaces these branches for
mandatory re-examination. High debt = gravitational pull on the trajectory.

**Convergence warning** — if the synthesis agent agrees with everything (high agreement rate)
AND the divergence agent's interrupt budget is unused, the ADHD agent may have been
captured by the synthesis agent's frame. This is system failure, not success.

**Relational context** — the coupling history between THIS pair of agents. Not portable
to a different session. If you restart ACE on the same topic, you lose the accumulated
coupling intelligence. Use `--state-file` to persist and inspect between sessions.
