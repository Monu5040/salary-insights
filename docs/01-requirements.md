# 01 · Requirements — ACME Salary Management (v1)

**Goal.** Replace the spreadsheets ACME's HR team uses for 10,000 employees across several countries with a web app where the HR Manager keeps salaries correct and answers questions about how the organization pays people in seconds.

**Persona.** One **HR Manager**, who owns salary data, records raises, and prepares numbers for leadership and finance.

**What's broken today.** Copies of the sheet drift, two people overwrite each other's cells, cross-country totals are converted by hand, and every question is a new pivot table.

## Success criteria
- Any employee found in **< 2 s**; the main pay questions answered in **≤ 3 clicks**.
- Every org-wide number says which currency it is in and how it was converted.
- Two people editing the same employee never silently overwrite each other.
- Live at a public URL, with 10,000 realistic employees.

## In scope — in priority order
1. **Employees**: add, edit and delete; search by name or code, filter by country and department, sort and page through 10,000 rows.
2. **Salary**: each employee's current annual gross base salary, in its own currency; a raise by amount or by %, previewed exactly before saving.
3. **Currencies**: salaries stay in their original currency; insights convert them into a reporting currency (USD by default, or any other) at fixed budget exchange rates.
4. **Insights**: headcount, payroll, median and mean; payroll and salary ranges by country and by department; salary statistics by job title; a group-by explorer (country, department, job title, tenure) for other questions; each employee against peers with the same job title.
5. **Seed data**: 10,000 realistic, deterministic employees.

## Deliberately left out
| Left out | Why |
|---|---|
| Sign-in and roles | One HR Manager persona; the brief asks for no authentication. The public demo holds made-up data only and is reset every night, so anyone may edit it. Needed before real data. |
| Salary history, back- and future-dated changes | Current salary is enough for the stated questions. Edits replace the salary, so a raise trend can't be shown. |
| Audit log and approvals | Changes are made directly by the decision-maker; neither is required. |
| Bonuses, allowances, equity | Base salary answers the questions; the model has room for more later. |
| Job levels, pay bands, compa-ratio bands | Not required; seniority is visible in job titles, and peers are compared by job title. |
| Part-time staff, contractors, FTE | Full-time employees only. |
| Gender pay-gap analysis, compliance and data residency | Not prescribed; no gender is stored. |
| CSV/Excel import and export | Optional; the demo is seeded instead. |
| Live exchange rates, rate history | Finance reports at fixed budget rates, and a feed would be an external point of failure. |
| Natural-language questions | Optional; the explorer covers ad-hoc questions. |
| Payroll processing, employee self-service, multiple organizations | A different product. |
| Extra infrastructure (Redis, job queues, Kubernetes) | Not justified: every query takes milliseconds at this size. |

## Assumptions
Fixed exchange rates are a reference-data list. USD is the reporting currency, and an employee may be paid in a currency other than their country's. Peers are people with the same job title, in the same country when there are at least 5, otherwise in every country. One organization time zone (UTC). [`02-design.md`](02-design.md) §2 lists where each assumption lives, so changing one means changing a setting or reference data, not code.

## Non-functional
**Correctness**: exact decimal money; amounts rounded only for display. **Speed**: server responses under 200 ms at 10,000 employees. **Security**: HTTPS, security headers and a content security policy, no personal data in logs, salary data never kept by shared caches. **Accessibility**: keyboard use and WCAG AA contrast. **Browsers**: current Chrome, Edge, Firefox and Safari on desktop.
