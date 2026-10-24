# 03 · Edge cases

How each case is handled and where it is tested. **U** domain unit · **I** API integration (real Postgres) · **F** frontend · **E** end-to-end.

## Money and currency
| # | Case | Behavior | Test |
|---|---|---|---|
| 1 | Floating-point drift | `Decimal` end to end, `NUMERIC` in the database, strings in JSON; a JSON number for a salary is refused | U, I, F |
| 2 | Currencies with 0 or 3 decimals (JPY, KWD) | An amount with more decimals than its currency allows is refused; display uses the currency's digits | U, I |
| 3 | Adding amounts in different currencies | Insights add only converted amounts; nothing sums raw amounts across currencies | U, I |
| 4 | A currency without a rate | Every stored salary has a rate (its currency is a foreign key, and a rate is required and positive); asking for an answer in an unknown currency is a 422 naming it, and the screen explains it | U, I, F |
| 5 | Paid in a currency other than the country's (an expat in USD) | Allowed; the form defaults to the country's currency and points out the difference; peers compare in the country's currency | I, F |
| 6 | A % raise that gives a sub-unit amount | Rounded half-up to the currency's minor unit; the preview shows the exact result and that amount is what is sent | U, F, E |
| 7 | Huge nominal amounts (IDR) | `NUMERIC(19,4)` holds them; strings avoid JavaScript precision loss; a per-currency ceiling refuses likely typos (extra zeros) | U, I |
| 8 | Zero or negative salary | Refused by the serializer and by a database constraint | U, I |

## Dates
| # | Case | Behavior | Test |
|---|---|---|---|
| 9 | "Today" differs by time zone | One organization time zone (setting, default UTC) through an injected clock; tenure bands use it | U, I |

## Identity and input
| # | Case | Behavior | Test |
|---|---|---|---|
| 10 | Duplicate employee code or email, differing only in case or spaces | Codes are trimmed and stored upper-case (letters, digits, `.`, `_`, `-`); emails are unique in any case; a clash is a 409 naming the field and the employee who has it, and the form links to them | U, I, F |
| 11 | Unicode names, apostrophes, single names, long names | One `full_name` field (1–200 chars), NFC-normalized; search is accent-insensitive (José ↔ jose) | U, I |
| 12 | Whitespace-only, overlong or malformed fields | Refused with field-level errors, shown under their fields | U, I, F |
| 13 | Unknown country, department or currency | 400 naming the field; foreign keys enforce it too | I |
| 14 | Client sends fields it must not set (id, version, search text) | Ignored: those fields aren't writable | I |

## Concurrent edits
| # | Case | Behavior | Test |
|---|---|---|---|
| 15 | Two people edit the same employee, or one edits while the other deletes | Every write sends the `If-Match` version it loaded; a stale one gets 412 with the current version, and Reload shows the other person's record in place of what was typed; a write without `If-Match` gets 428 | I, F, E |
| 16 | Double-clicked Save or a network retry when adding | The unique code and email turn a repeat into a 409 pointing to the first record, never a duplicate; the button is disabled while saving | I, F |
| 17 | Saving without changing anything | No version bump, so nobody else's open copy goes stale for nothing | I |

## Queries and analytics
| # | Case | Behavior | Test |
|---|---|---|---|
| 18 | Page past the end; huge page size | Empty page with the correct total (DRF's default would be a 404); page size capped at 200 | I |
| 19 | Unstable order across pages (equal names) | Every sort ends with `id` as tie-breaker | I |
| 20 | Search containing `%`, `_`, `\` or quotes | Parameterized and matched literally | I |
| 21 | Sort, filter or metric on an arbitrary column | Allow-listed; anything else is a 400 naming the parameter (DRF's default silently ignores unknown sort fields) | I, F |
| 22 | A filter that matches nobody | 200 with a headcount of 0 and null statistics, never a division by zero | U, I |
| 23 | Groups too small to read much into | Shown but flagged `low_sample` below `MIN_GROUP_SIZE` | I, F |
| 24 | Peer group too small | Same job title in every country instead of one; the answer names the group used | U, I, F |
| 25 | A job title nobody else has | Zero peers: no median, percentile or compa-ratio, and the card says so | I |
| 26 | About 70 job titles in one table | Paged and sortable, rather than one very long card | F |

## Security and privacy
| # | Case | Behavior | Test |
|---|---|---|---|
| 27 | Salary data kept by a shared cache | Every API response sends `Cache-Control: private, no-cache` | I |
| 28 | Anyone can edit the open demo | Only generated data is there, and a timer reseeds it every night at 03:00 UTC | — |
| 29 | Script injected into a page | A Content Security Policy on every response: only this site's scripts, never inline ones (the API docs included); inline styles only, for Ant Design; no framing, plugins or `<base>`. The built app runs with no violations | I, E |

## Operations
| # | Case | Behavior | Test |
|---|---|---|---|
| 30 | Seed run twice, or against production | Needs `--reset`; runs only when `ENV` is `dev`, `test` or `demo` (an allow-list, so a missing or misspelled value refuses) | I |
| 31 | A deploy whose checks or migrations fail | `deploy.sh` runs `check --deploy`, `collectstatic` and `migrate` before switching releases, so the previous release keeps serving | — |
| 32 | An unknown API address, or an error no view handled | A problem (`application/problem+json`) with the request id, never Django's HTML page; a crash never shows the error itself, which may hold data. The app shows the request id to quote | I, F |
| 33 | A model changed without a migration | `makemigrations --check` fails CI | — |
| 34 | Insecure production settings (`DEBUG`, HSTS, cookies) | `check --deploy --fail-level WARNING` fails CI and the deploy | — |
| 35 | The app isn't built when Django serves its page | A plain 404 saying how to build it; unknown API and static addresses stay 404s instead of returning the app | I |

## Screens
| # | Case | Behavior | Test |
|---|---|---|---|
| 36 | A page that breaks while drawing | Only that page shows "Something went wrong on this page" with Reload; the menu and other pages keep working | F |
| 37 | A link to an address the app has no page for | "Page not found" with a way to Insights, instead of quietly landing somewhere else | F |
| 38 | Directory filters that match nobody | Says so, with a button that clears the filters and keeps the sort | F |
| 39 | Using the app by keyboard or with a screen reader | A skip link past the sidebar; one heading per page, which names the tab; every field labelled, required ones announced; charts read as text; WCAG AA contrast. axe finds nothing on any page or dialog | F, E |
| 40 | Chart rows with words of different lengths beside their bars | Every bar in a chart is drawn on a track of the same width, so lengths compare across rows | E |
