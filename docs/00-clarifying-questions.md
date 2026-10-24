# 00 · Clarifying questions

Sent to the interviewer before any code was written. Each question is one whose answer changes the design, and each carries the assumption I would build on without an answer, so work never blocks on a reply. The answers are at the end.

| # | Question | Why it changes the design | Working assumption |
|---|---|---|---|
| 1 | **Users.** One HR manager, or an HR team where some people should see only their own country, or only read? | Auth model; whether every query needs country-level row scoping. | Two roles: **HR Admin** (full) and **HR Viewer** (read-only). Country scoping deferred — every row carries a country, so it can be added. |
| 2 | **What "salary" means.** Annual base pay only, or total compensation (bonus, allowances, equity)? | Compensation schema; every analytic. | Annual base salary; the model leaves room for other components. |
| 3 | **History.** Effective-dated history of changes with reasons (hire, raise, promotion, correction), including back-dated corrections and future-dated changes (an appraisal effective 1 April, entered in March)? | A column vs. a time series; "as-of" reporting; raise analytics. | Full history; back- and future-dated changes allowed; current salary derived for any date. |
| 4 | **Currencies.** Which countries? Is anyone paid in a currency other than their country's (expats paid in USD)? For org-wide numbers, which reporting currency — and fixed budget FX rates or market rates? | Totals across countries are wrong without conversion; finance usually reports at fixed budget rates. | Currency stored per salary record; USD reporting currency; admin-maintained, dated FX rates seeded from a fixed snapshot; no live FX feed. |
| 5 | **Questions to answer.** I'm planning for: payroll cost by country and department, salary ranges by role/level/country, an employee vs. their peers, pay outliers, gender pay gap within the same level, and raise trends. Anything missing? Is natural-language querying expected? | The analytics surface. | Curated insights plus a group-by explorer for ad-hoc questions; natural-language questions are a stretch goal. |
| 6 | **Pay structure.** Are there job levels/grades, and pay bands per level and country? | Bands enable compa-ratio and out-of-band reports. | Levels L1–L7; no bands, so employees are compared with their peer median. |
| 7 | **Moving off Excel.** Should HR be able to bulk-import the existing spreadsheets? Could you share a sample layout? If some rows are invalid, reject the whole file or import the valid rows? | Import format, validation and failure semantics. | CSV import → validation preview with row-level errors → all-or-nothing commit. CSV export of any filtered view. |
| 8 | **Control.** Do salary changes need approval (maker-checker), or is the HR manager the final authority? | Approvals are long-running, human-in-the-loop workflows — a different subsystem. | No approvals; every change audited (who, when, why, before → after). |
| 9 | **Workforce types.** Part-time staff, contractors, hourly workers? | A 0.5 FTE salary compared with a full-time one is misleading. | Full- and part-time with an FTE; amounts annual; comparisons FTE-normalized; contractors excluded. |
| 10 | **Sensitive data.** Is storing gender for pay-equity analysis acceptable? Any GDPR, data-residency or retention rules — can records be deleted, or only terminated? | Legal constraints; whether hard deletes exist. | Gender optional (incl. "undisclosed"); employees are terminated, never hard-deleted; groups under 5 people are flagged as low-sample; the adjusted pay gap uses only cells with at least 5 women and 5 men. |
| 11 | **Scale and logistics.** Expected growth beyond 10k, number of concurrent users, hosting preference, and the expected time-box? | Sizing; how far to take hardening. | ≤ 50 concurrent users with headroom to ~100k employees; Docker + managed Postgres. |

## Answers

The interviewer replied before any code was written. Each answer, and what it changed:

| # | Answer | Decision |
|---|---|---|
| 1 | A single HR Manager persona; no authentication or role-based access | One persona, no sign-in. The public demo is open, so its data is reset every night |
| 2 | Annual gross base salary for full-time employees | One salary per employee: an amount and its currency |
| 3 | Current salary is enough; effective-dated history is optional | Effective-dated history, back- and future-dated, with the current salary derived for any day |
| 4 | Keep original currencies, or one reporting currency at fixed rates; no live rates | Salaries stay in their own currency; insights convert to a reporting currency (USD by default) at fixed budget rates kept as reference data |
| 5 | Focused dashboards and breakdowns by country, department or job title; pay equity and natural language optional | A dashboard of those breakdowns plus a group-by explorer, and each employee against peers with the same job title. Pay equity compares people in the same role, without gender (see 10). No natural-language questions: the explorer covers ad-hoc ones |
| 6 | Job levels and pay bands not required | No levels or bands; seniority shows in the job title |
| 7 | CSV/Excel import and export optional | CSV import with a preview, applied whole or not at all; CSV export of the directory |
| 8 | Changes can be made directly; approvals not required, audit history optional | Direct edits, no approvals and no audit log; the salary history records each change's date and reason. Concurrent edits are still detected |
| 9 | Full-time employees only; no contractors or FTE | No employment types or FTE |
| 10 | No gender analysis or compliance requirements prescribed | No gender field. Employees can be deleted |
| 11 | 10,000 employees; no concurrency target or hosting preference; a live public URL is expected | Sized for 10,000; deployed to one VM with a public HTTPS address |

[`01-requirements.md`](01-requirements.md) is written from these answers.
