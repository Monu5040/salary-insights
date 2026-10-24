# 01 · Requirements — ACME Salary Management (v1)

**Goal.** Replace the spreadsheets ACME's HR team uses for 10,000 employees across several countries with a web app where the HR Manager keeps salaries correct and answers questions about how the organization pays people in seconds.

**Persona.** One **HR Manager**, who owns salary data, records raises, and prepares numbers for leadership and finance.

**What's broken today.** Copies of the sheet drift, two people overwrite each other's cells, cross-country totals are converted by hand, and every question is a new pivot table.

## Success criteria
- Any employee found in **< 2 s**; the main pay questions answered in **≤ 3 clicks**, or one typed question.
- Every salary change says when it took effect and why; the existing sheet imports with row-level feedback and **never partially**.
- Every org-wide number says which currency it is in and how it was converted.
- Two people editing the same employee never silently overwrite each other.
- Live at a public URL, with 10,000 realistic employees.

## In scope — in priority order
1. **Employees**: add, edit and delete; search by name or code, filter by country and department, sort and page through 10,000 rows.
2. **Salary history**: annual gross base salary as dated changes with a reason (merit, promotion, market, transfer, correction). Changes can be back-dated or future-dated; the current salary is the one in force today. A raise can be entered by amount or by %, and is previewed exactly before saving.
3. **Currencies**: salaries stay in their original currency; insights convert them into a reporting currency (USD by default, or any other) at fixed budget exchange rates.
4. **Insights**, on any date: headcount, payroll, median and mean; payroll and ranges by country and department; salary by job title; a group-by explorer; each employee against peers with the same job title.
5. **Pay equity**: people paid far from others in the same role (outside 80–120% of their peers' median), furthest out first. No gender data is used.
6. **Questions in plain English**: one question box. Groq turns the question into explorer parameters (never SQL) and the explorer answers it.
7. **CSV in and out**: import a sheet saved from Excel (preview with row errors, then apply the whole file or nothing); export the filtered directory as CSV that Excel opens correctly.
8. **Seed data**: 10,000 realistic, deterministic employees with salary history.

## Deliberately left out
| Left out | Why |
|---|---|
| Sign-in and roles | The brief asks for one HR Manager persona and no authentication. The public demo holds made-up data only and is reset every night, so anyone may edit it. Needed before real data. |
| Gender and gender pay-gap analysis | Not prescribed, and gender is sensitive data. Pay equity compares people in the same role instead. |
| Audit log and approvals | Changes are made directly by the decision-maker; the salary history already says what changed when and why. |
| Bonuses, allowances, equity | Base salary answers the questions; the history has room for more later. |
| Job levels and pay bands | Not required; seniority shows in job titles, and peers are compared by job title. |
| Part-time staff, contractors, FTE | Full-time employees only. |
| Compliance and data-residency rules | Not prescribed. |
| `.xlsx` files | Excel saves and opens CSV; reading workbooks would add a library for no extra answers. |
| Live exchange rates, rate history | Finance reports at fixed budget rates, and a feed would be an external point of failure. |
| Payroll processing, employee self-service, multiple organizations | A different product. |
| Extra infrastructure (Redis, job queues, Kubernetes) | Not justified: queries take milliseconds and a 10,000-row import about a second. |

## Assumptions
Fixed exchange rates are a reference-data list. USD is the reporting currency, and an employee may be paid in a currency other than their country's. Peers are people with the same job title, in the same country when there are at least 5, otherwise in every country. One organization time zone (UTC). A question's text is sent to Groq, with the lists of countries and departments; no salary data is. [`02-design.md`](02-design.md) §2 lists where each assumption lives, so changing one means changing a setting or reference data, not code.

## Non-functional
**Correctness**: exact decimal money; amounts rounded only for display. **Speed**: server responses under 200 ms at 10,000 employees. **Security**: HTTPS, security headers and a content security policy, no personal data in logs, salary data never kept by shared caches. **Accessibility**: keyboard use and WCAG AA contrast. **Browsers**: current Chrome, Edge, Firefox and Safari on desktop.
