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
- "Use this VM to host the application, use CD to deploy", then "deploy using a script, not a Dockerfile".
- "CSV/Excel import and export, pay-equity analysis and natural-language querying are optional, effective-dated history and backdated or future-dated changes are optional. Add this", then "add only must-have features" and "don't include features that the interviewer said are not required". The AI asked how questions should be understood (Groq), built minimal versions, and dropped the gender field it had started on, since gender-based pay analysis is not prescribed: pay equity compares people in the same role instead.
- "You have overcomplicated it. Keep it simple, so that anyone can understand it, and give the high-level flow of all the features."
- "You have made the UI, but I don't think it's attractive", then "don't worry about phone layout". The AI screenshotted every screen first, said what made each look plain, and kept the end-to-end and accessibility tests passing through the refresh.

## Where the AI was wrong, and how it was caught

| What the AI produced | What was wrong | How it was caught | Outcome |
|---|---|---|---|
| A health-check option added to the database pool settings (M1) | Django 5.2 already passes that check when `CONN_HEALTH_CHECKS = True`; passing it twice crashes at startup | Read `django/db/backends/postgresql/base.py` | Settings use `CONN_HEALTH_CHECKS = True` |
| Redirect exemptions written as `/healthz/` (M1) | Django matches `SECURE_REDIRECT_EXEMPT` against the path without its leading slash, so health checks would be redirected | Checked Django's source | Patterns are `^healthz/` and `^readyz/` |
| `parse_amount` (M2) | It checked decimal places before size, so a 40-digit input crashed with `decimal.InvalidOperation` instead of "too large" | Code review, then a failing test written first | The size check runs first; the test pins it |
| Test settings with `--reuse-db` on by default (M3) | A test that commits for real flushes the database when it finishes, so the next run started with no reference data | Running the file on its own, twice | Each run gets a fresh test database; `--reuse-db` is opt-in |
| The seed reset test without `SET CONSTRAINTS ALL IMMEDIATE` (M3) | Django creates foreign keys `DEFERRABLE INITIALLY DEFERRED`, so `TRUNCATE` inside the test's transaction refused the pending checks | The test, on its first run | The test checks constraints per statement, with a comment saying why |
| An "unknown currency" case in the database-rules test (M3) | The same deferred foreign keys are checked only at commit, which a rolled-back test never reaches | The test, on its first run | The serializer test covers unknown currencies; the rules test keeps the checks that fire at once |
| Formatting the new frontend files (M6) | It ran Prettier through `npx`, which the project doesn't use: it was downloaded on the fly and reformatted files outside the change | Reading `git diff --stat` before committing | Those files were restored and the new ones written in the project's style |
| Reload after "someone else changed this employee" (M6) | The edit form fetched their version but kept what had been typed, because Ant Design keeps typed values over new initial ones; the unit test never typed before reloading | The browser test with two people editing one employee | The form resets to the server's record when its version changes; the unit test types first |
| Accessibility checks that passed or failed by timing (M7) | Pages were scanned while a dialog was still fading in and before every card had loaded | Running the suite repeatedly | Scans wait for animations to end and for every card |
| Hiding Ant Design's duplicate `aria-required` from axe (M7) | The AI reached for `omitDomProps`, a prop rc-select keeps private, so the fix would have done nothing | The type checker refused it, then reading rc-select's source | The one known finding is left out of the axe check, with the reason, and a test checks each required combobox carries `aria-required` |
| The bar charts on Insights (M6) | Each row was laid out on its own, so the room for its bar depended on the words beside it, and longer labels drew shorter bars | Reviewing screenshots | Rows share one grid (CSS subgrid); a browser test checks every bar has the same track width (edge case #40) |
| The header on narrow screens (M7) | The accessibility pass claimed WCAG 2.2 AA, but every scan ran at desktop width | Screenshots at phone width | Phones are out of scope; design §8 says AA at desktop sizes |
| Removing the CSRF middleware with sign-in (M8) | `check --deploy --fail-level WARNING` refused the settings, which would have stopped every deploy | The deploy script's own check, on the first deploy | The middleware stays (DRF's views are exempt) and the CSRF cookie is `Secure` |
| The first VM setup command (M8) | The SSH public key was passed to `ssh … bash -s` unquoted, so it split into words: the key became `ssh-ed25519` and the site name the key's body | Reading the script's last line, "VM ready for AAAAC3…" | Arguments quoted; the bad user key and secrets removed and made again |
| The deploy's "seed an empty database" check (M8) | Django 5.2's `shell` prints "8 objects imported automatically" before the output, so the check never saw `False` and the live site had no employees | The live summary said headcount 0 | `shell --no-imports` |
| Pay equity with a gender field (M9) | The brief lists pay equity as optional but gender-based pay analysis as not prescribed, so storing gender went past it | The user's "don't include what the interviewer said is not required" | Removed before any commit; pay equity compares people in the same role |
| The import preview's `errors` list (M9) | DRF serializers already have an `.errors` attribute, so a field of that name broke the schema | mypy | The field is `row_errors` |
| The expected pay-equity list in the test (M9) | Worked out by hand, it missed Ivan, whose $100,000 is 2.02 times his peers' median, and rounded Hana's ratio up | The test, on its first run | The comment in the test now works every ratio through |
| HTTPS on the VM with Caddy and Let's Encrypt (M8) | Validation failed. The AI first guessed a path-MTU problem and tried clamping the TCP MSS, which changed nothing | A packet capture on the VM: the provider forwards the handshake but drops data from some of Let's Encrypt's validation regions | A Cloudflare quick tunnel from the VM, so no inbound port or certificate is needed; the MSS rule was removed |

## Rules I keep while building

- Every library or database claim is checked against official docs or source.
- Scope stays mine: the AI proposes and I decide.
- New prompts and new mistakes are added to this file as the build goes on.
