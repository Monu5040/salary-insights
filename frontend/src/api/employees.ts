import { getJson, ifMatch, sendJson } from "./http";

export type EmployeeRow = {
  id: number;
  employee_code: string;
  full_name: string;
  country: { code: string; name: string };
  department: { id: number; name: string };
  job_title: string;
  hire_date: string;
  /** Annual gross base salary, as a decimal string at its currency's decimals. */
  salary: string;
  currency: string;
};

export type Employee = EmployeeRow & {
  email: string;
  version: number;
  updated_at: string;
};

export type Page<T> = { count: number; page: number; page_size: number; results: T[] };

/** What a form sends: references by code or id, money as a string. */
export type EmployeeInput = {
  employee_code: string;
  full_name: string;
  email: string;
  country: string;
  department: number;
  job_title: string;
  hire_date: string;
  salary: string;
  currency: string;
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

export const createEmployee = (input: EmployeeInput) => sendJson<Employee>("POST", BASE, input);

export const updateEmployee = (id: number, version: number, input: Partial<EmployeeInput>) =>
  sendJson<Employee>("PATCH", `${BASE}${id}/`, input, ifMatch(version));

export const deleteEmployee = (id: number, version: number) =>
  sendJson<undefined>("DELETE", `${BASE}${id}/`, undefined, ifMatch(version));
