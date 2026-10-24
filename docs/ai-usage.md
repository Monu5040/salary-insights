# AI usage

How AI tools were used on this project, the prompts that shaped it, and where the AI was wrong and how that was caught. Updated as the build goes on.

## Tools and approach

- **Claude Code** is the pair programmer. It drafts, reviews and checks; I decide scope and review every change before it lands.
- **`CLAUDE.md`** fixes the conventions (layers, money, dates, configuration, tests) so generated code stays consistent.
- **Tests first** for money, conversion and statistics: generated code has to pass tests I wrote or reviewed. Nothing lands on "looks right".
- **Library claims are checked** against official docs or source before they go into the design or the code.

## How the design was produced

1. **Questions before code.** Clarifying questions went to the interviewer, each with the assumption I would otherwise build on (`00`).
2. **Answers fix the scope.** The interviewer's answers narrowed it a lot: no sign-in, current salary only, no import or export, no audit, levels or gender. The one-page requirements (`01`) list each of these under "Deliberately left out", with the reason.
3. **Design, edge cases and plan** (`02`–`04`), then code, one milestone at a time.

## Prompts that shaped the work

- The interviewer's clarification, pasted in full, with: "remove the commit that is beyond requirement, build as if you have started implementation after requirement gathering". The AI asked which optional items to cut (all of them), whether to rebuild the history (yes, as in-scope commits), and what the open demo should do without sign-in (reset nightly).
- "You have overcomplicated it. Keep it simple, so that anyone can understand it, and give the high-level flow of all the features."

## Where the AI was wrong, and how it was caught

| What the AI produced | What was wrong | How it was caught | Outcome |
|---|---|---|---|

## Rules I keep while building

- Every library or database claim is checked against official docs or source.
- Scope stays mine: the AI proposes and I decide.
- New prompts and new mistakes are added to this file as the build goes on.
