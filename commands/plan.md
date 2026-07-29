---
description: Turn a settled decision into an ordered, falsifiable execution plan (GOVERNOR mode, single strong model)
argument-hint: "[what to plan]"
---

You are handling the `/ACE:plan $ARGUMENTS` command.

`/ACE:plan` is the **convergent** half of ACE. It takes a decision that is **already made** and
returns an ordered sequence of steps, each stating what would falsify it and what observation
gates the next one. It runs on a single strong model — you — by design. Do not recruit a weak
peer; a weak peer defers from incapacity, not judgment, and that is indistinguishable from
agreement.

Do this:

1. **Read the skill in full:** `skills/ace-plan/SKILL.md` in this plugin. It carries the
   falsifiable-step template, the GOVERNOR-mode framing, the optional decorrelated review pass,
   and the worked example. Follow it; do not improvise a different plan format.

2. **Check the boundary before anything else.** If the decision is *not* settled — the user is
   still choosing between options, or cannot name a rejected alternative — stop and route to
   `/ACE:debate` instead. Say so explicitly rather than silently producing a plan over an open
   question. If the request contains both ("plan it and tell me if it's the right call"), run
   debate first, then plan, and say that is what you are doing.

   Same boundary in the other direction: if the user arrives **with an existing plan, RFC, or
   design doc** and wants it attacked, critiqued, or red-teamed, that is `/ACE:debate`
   (`--preset frames-adversarial`), not this command. The review pass in step 5 is not an
   entry point — it only ever runs on a plan this command just authored.

3. **Topic:** if `$ARGUMENTS` is non-empty, treat it as the thing to plan. If empty, ask for
   the decision and the alternatives that were rejected.

4. **Write the finished plan to a file** (default `PLAN.md` in the project root) so it outlives
   the conversation and can be read by the optional review pass.

5. **Offer the optional decorrelated pass** only after the plan is finished, and only if the
   plan is hard to reverse or depends on external facts. One pass per risk — never compare two
   seats and count concurrence. Protocol and prompts:
   `skills/ace-plan/references/decorrelated-review.md`. Gate the result yourself: an empty or
   off-topic reply is a FAILED pass, and `agy.sh` returns empty output as exit 0, so check the
   content and not just the exit code.

The `ace` CLI is **not required** for this command — planning is synthesis, and this
conversation is the synthesis engine. See `skills/ace-plan/references/cli-scaffolding.md` for
the minority of cases where running the engine alongside a plan helps, and note that the
globally installed `/usr/local/bin/ace` is stale relative to this repo.
