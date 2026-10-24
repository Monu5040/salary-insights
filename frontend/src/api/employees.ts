import { getJson, ifMatch, sendJson } from "./http";

export type EmployeeRow = {
  id: number;
  employee_code: string;
  full_name: string;
  country: { code: string; name: string };
  department: { id: number; name: string };
  job_title: string;
  hire_date: string;
  /** The annual gross base salary in force today, at its currency's decimals; null for
   *  someone whose first salary starts later. */
  salary: string | null;
  currency: string | null;
};

export type Employee = EmployeeRow & {
  email: string;
  version: number;
  updated_at: string;
};

export type Page<T> = { count: number; page: number; page_size: number; results: T[] };

/** What the edit form sends: references by code or id. The salary changes through its
 *  history. */
export type EmployeeInput = {
  employee_code: string;
  full_name: string;
  email: string;
  country: string;
  department: number;
  job_title: string;
  hire_date: string;
};

/** A new employee comes with their starting salary, effective on the hire date. */
export type NewEmployeeInput = EmployeeInput & { salary: string; currency: string };

export type Reason = "hire" | "merit" | "promotion" | "market" | "transfer" | "correction";

export type SalaryRow = {
  id: number;
  effective_date: string;
  amount: string;
  currency: string;
  reason: Reason;
  note: string;
  /** Against the change before, in the same currency; null when it isn't a raise. */
  raise_percent: string | null;
  currency_change: boolean;
  /** Takes effect after today. */
  scheduled: boolean;
};

export type SalaryHistory = {
  employee_version: number;
  /** The change in force today. */
  current_id: number | null;
  /** Newest first. */
  records: SalaryRow[];
};

/** A change as the form sends it: always the amount, never a % (design §6). */
export type SalaryChangeInput = {
  effective_date: string;
  amount: string;
  currency: string;
  reason: Reason;
  note: string;
};

/** The salary against colleagues with the same job title, in the country's currency. */
export type PeerPosition = {
  currency: string;
  definition: string;
  peers: number;
  low_sample: boolean;
  pay: string;
  p10: string | null;
  p25: string | null;
  median: string | null;
  p75: string | null;
  p90: string | null;
  /** Share of peers paid less, 0 to 100. */
  percentile_rank: string | null;
  compa_ratio: string | null;
};

/** The directory's parameters: the same in the page's address and in the API's. */
export const DIRECTORY_PARAMS = ["q", "country", "department", "sort", "page", "page_size"] as const;

const BASE = "/api/v1/employees/";

export const listEmployees = (query: string) => getJson<Page<EmployeeRow>>(`${BASE}?${query}`);
export const fetchEmployee = (id: number) => getJson<Employee>(`${BASE}${id}/`);
export const fetchPeers = (id: number) => getJson<PeerPosition>(`${BASE}${id}/peers/`);

/** The directory as CSV, with the same filters: a plain link, as the browser downloads it. */
export const exportUrl = (query: string) => `/api/v1/exports/employees.csv?${query}`;

export const createEmployee = (input: NewEmployeeInput) =>
  sendJson<Employee>("POST", BASE, input);

export const updateEmployee = (id: number, version: number, input: Partial<EmployeeInput>) =>
  sendJson<Employee>("PATCH", `${BASE}${id}/`, input, ifMatch(version));

export const deleteEmployee = (id: number, version: number) =>
  sendJson<undefined>("DELETE", `${BASE}${id}/`, undefined, ifMatch(version));

const salaries = (id: number) => `${BASE}${id}/salaries/`;

export const fetchSalaries = (id: number) => getJson<SalaryHistory>(salaries(id));

export const recordChange = (id: number, version: number, input: SalaryChangeInput) =>
  sendJson<SalaryHistory>("POST", salaries(id), input, ifMatch(version));

export const correctChange = (
  id: number,
  version: number,
  changeId: number,
  input: Partial<SalaryChangeInput>,
) => sendJson<SalaryHistory>("PATCH", `${salaries(id)}${changeId}/`, input, ifMatch(version));

export const removeChange = (id: number, version: number, changeId: number) =>
  sendJson<SalaryHistory>("DELETE", `${salaries(id)}${changeId}/`, undefined, ifMatch(version));
