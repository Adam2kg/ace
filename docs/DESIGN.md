# ACE System Documentation for Claude Code Operators

This document describes the fully redesigned ACE (Adaptive Cognitive Engine) system, intended for operators leveraging Claude Code for advanced cognitive scaffolding.

## ARCHITECTURE OVERVIEW

ACE operates on two fundamental root modes, dictating its approach to information processing and synthesis:

*   **MIRROR Mode (Human Thinking Scaffold):**
    *   **Goal:** Maximize entropy, amplify divergence, and reflect gently. This mode is designed to support and extend human thought, encouraging broad exploration and maintaining cognitive flexibility.
    *   **Activation:** Automatically engaged when `human-mode` presets are active.
*   **GOVERNOR Mode (AI Thinking Scaffold):**
    *   **Goal:** Minimize entropy, converge ideas, and synthesize rigorously. This mode is optimized for AI-driven processes, aiming for efficient synthesis and focused problem-solving.
    *   **Activation:** Automatically engaged when AI-only presets are active.

### Core Cognitive Metrics: ScoreVector

ACE evaluates thought states using a multi-dimensional `ScoreVector`, informing its scaffolding decisions:

*   **novelty:** The degree of new information or unexpected connections.
*   **coherence:** The logical consistency and internal integrity of ideas.
*   **frame_saturation:** How thoroughly a particular conceptual framework or metaphor has been explored.
*   **resonance:** Cross-branch echoing; the extent to which ideas or themes recur and interact across different lines of inquiry.
*   **depth_pressure:** The demand for unresolved elaboration; signals areas requiring further investigation or detail.

### Synthesis Weight Functions

Two distinct functions govern how ACE synthesizes information, tailored to its operating mode:

*   **`synthesis_weight_mirror()`:** Used in MIRROR mode. Employs a weighted sum approach, designed to protect "escape vectors" and prevent premature convergence, thereby fostering continued divergence.
*   **`synthesis_weight_governor()`:** Used in GOVERNOR mode. Implements a product-gated novelty mechanism, requiring both high coherence AND resonance for synthesis to proceed, ensuring robust and interconnected insights.

### Overthinking Detection: `overthinking_warning()`

This warning system fires *only* in human-mode presets to distinguish between unproductive rumination and genuine deepening of thought:

*   **Circular Visits:** Detected when `stagnant delta < 0.08`, indicating repetitive exploration without new insights. Triggers an "overthinking" warning.
*   **Depth Attraction:** Represents genuine deepening into a topic. Generates a `DepthAttractorSignal` (positive, not a warning).

## PRESETS: Attentional Topology

ACE presets calibrate its behavior based on **ATTENTIONAL TOPOLOGY** (breadth vs. depth), rather than specific task domains.

*   **`human-adhd` (Calibration: 'Explorer')**
    *   **Purpose:** Broad-scan exploration, initial ideation, or navigating complex, loosely defined problems.
    *   **Calibration:** High interrupt budget (`=8`), low debt threshold (`=2.0`), high resonance_weight (`=0.80`), low closure_pressure (`=0.20`).
    *   **Usage:** Default for `--human-mode`. Use when you need to generate a wide array of ideas, explore tangential connections, and avoid getting stuck on a single path.
    *   *Calibration pending — design intent, not observed use.*
*   **`human-scientific` (Calibration: 'Deep Focus')**
    *   **Purpose:** Narrow-channel investigation, detailed analysis, or converging on specific hypotheses.
    *   **Calibration:** Low interrupt budget (`=3`), high debt threshold (`=6.0`), lower resonance_weight (`=0.40`), high closure_pressure (`=0.65`).
    *   **Usage:** Use when you need to delve deeply into a particular line of inquiry, systematically test assumptions, and drive towards a conclusive understanding.
    *   *Calibration pending — design intent, not observed use.*
*   **`human-creative`**
    *   **Alias for `human-adhd`**. Provides an identical calibration but with a different semantic label for user convenience.

**Calibration Labels shown to user:** 'Explorer' and 'Deep Focus'. Internal preset names (`human-adhd`, `human-scientific`) are not exposed directly to the end-user.

## CLI FLOW: The Paste-Cycle-Loop UX

ACE is designed to work in conjunction with Claude Code, forming an iterative "paste-cycle-loop." ACE *generates prompts*; Claude Code *is the synthesis engine*.

**Command Structure:**

```bash
ace run topic --preset human-adhd --human-mode --cycles N
```

**Workflow:**

1.  **Initial Run:** Execute `ace run` with your topic, chosen preset, and the desired number of cycles (`N`).
2.  **Divergence (Branches Generated):** After each cycle, ACE generates multiple conceptual branches based on its internal state and ScoreVector analysis.
3.  **Coupling Evaluation:** ACE evaluates the relationships and interdependencies (coupling) between the generated branches.
4.  **Synthesis Decision Menu:** Based on the coupling evaluation, ACE presents a numbered menu of synthesis options:
    *   `[1] Tensions`: Focuses on contradictions or unresolved conflicts between branches.
    *   `[2] Hidden question`: Aims to uncover underlying questions implied by the current state of knowledge.
    *   `[3] Uncomfortable branch`: Prioritizes a less explored or counter-intuitive branch, acting as an "escape vector" from common thought patterns.
    *   `[4] Full Mirror (default)`: Reflects the current state of all branches without explicit directional guidance, typically used for comprehensive feedback.
5.  **User Selection:** The user picks one number from the menu.
6.  **Focused Prompt Generation:** ACE generates a focused prompt in a dedicated panel, tailored to the chosen synthesis option.
7.  **Claude Code Integration:**
    *   **User Action:** The user copies the prompt from the ACE panel.
    *   **Paste into Claude Code:** The user pastes this prompt into their Claude Code environment.
    *   **Read Response:** The user reads and internalizes Claude Code's response.
    *   **Next Cycle:** The user initiates the next `ace run` cycle, potentially refining the topic or choosing a different synthesis option based on Claude Code's output.

**This is the core UX: ACE generates prompts; Claude Code is the synthesis engine.**

### Diagnosing Misbehaving Coupling

If ACE's coupling evaluation seems off, or the synthesis menu options don't align with your cognitive needs:

*   **Review ScoreVector:** Examine the raw `ScoreVector` output (if available) for unexpected values in novelty, coherence, resonance, or depth_pressure.
*   **Adjust Preset:** Switch to a different preset (`human-adhd` for broader scan, `human-scientific` for deeper focus) to alter ACE's attentional topology.
*   **Force "Uncomfortable Branch":** If you suspect ACE is converging too quickly or missing critical perspectives, explicitly select `[3] Uncomfortable branch` to force exploration of divergent paths.
*   **Inject External Stimuli:** Manually introduce new information or a different framing into Claude Code's response to influence ACE's next cycle.

## FRAME MONOCULTURE DETECTION

ACE includes a mechanism to detect when the inquiry is trapped within a single conceptual domain.

*   **Trigger:** Fires when all generated branches consistently share the same underlying metaphor domain.
*   **Warning:** `Frame monoculture detected — all branches use [domain] framing. A perspective shift might reveal what this frame hides.`
*   **Action:** When this warning appears, consider manually re-framing your topic, or explicitly selecting `[3] Uncomfortable branch` to break out of the dominant metaphor.

## RETAINED CONCEPTS FROM OLD ACE SYSTEM

The following concepts remain relevant in the redesigned ACE:

*   **Attractor Debt Explanation:** The mechanism by which ACE tracks unresolved cognitive effort or unexplored avenues, which contributes to `depth_pressure`.
*   **Convergence Warning Concept (Reframed):** While general convergence warnings are suppressed in MIRROR/human-mode (to encourage divergence), the underlying concept of premature closure is now addressed by the `overthinking_warning` and `frame_monoculture_detection`, as well as the deliberate "escape vectors" in the synthesis menu.
*   **Sophisticated Echo Warning:** Similar to `resonance`, this refers to the detection of recurring patterns or themes across different lines of inquiry, indicating deep structural connections.
*   **The Paste-Cycle-Loop:** As described above, this remains the primary and central user experience for interacting with ACE.

## QUALITY REQUIREMENTS FOR ACE TOOL IMPLEMENTATION

For the ACE tool itself, the following quality standards are expected:

*   **Help Text:** Comprehensive and clear help information accessible via `--help` flag.
*   **Exit Codes:** Meaningful and consistent exit codes to indicate success or specific failure modes.
*   **Standard I/O:** Correct and idiomatic use of `stdin`, `stdout`, and `stderr` for input, output, and error reporting, respectively.
*   **Argument Validation:** Robust validation of all command-line arguments with clear, user-friendly error messages for invalid inputs.