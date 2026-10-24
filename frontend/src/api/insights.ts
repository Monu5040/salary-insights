import { getJson } from "./http";

/** What every number in an answer is relative to (design §4). */
export type Answer = {
  as_of: string;
  currency: string;
  fx_basis: string;
};

export type Summary = Answer & {
  headcount: number;
  payroll: string;
  median: string | null;
  mean: string | null;
};

export type Metric =
  | "headcount"
  | "payroll"
  | "mean"
  | "median"
  | "p10"
  | "p25"
  | "p75"
  | "p90"
  | "min"
  | "max";

export type Dimension = "country" | "department" | "title" | "tenure";

export type Group = {
  keys: Partial<Record<Dimension, string>>;
  labels: Partial<Record<Dimension, string>>;
  headcount: number;
  low_sample: boolean;
  values: Partial<Record<Metric, string | null>>;
};

export type Exploration = Answer & { metrics: Metric[]; by: Dimension[]; groups: Group[] };

/** Someone paid far from others with the same job title (design §4 Pay equity). */
export type Outlier = {
  id: number;
  employee_code: string;
  full_name: string;
  country_name: string;
  job_title: string;
  pay: string;
  peer_median: string;
  compa_ratio: string;
  definition: string;
  peers: number;
};

export type PayEquity = Answer & {
  /** Compa-ratios inside this band are not flagged, such as ["0.80", "1.20"]. */
  band: [string, string];
  count: number;
  page: number;
  page_size: number;
  results: Outlier[];
};

/** The explorer parameters a question became. */
export type Preset = {
  id: string;
  title: string;
  chart: "bars" | "ranges" | "table";
  metrics: Metric[];
  by: Dimension[];
};

const BASE = "/api/v1/analytics/";

export const fetchSummary = (scope: string) => getJson<Summary>(`${BASE}summary/?${scope}`);
export const fetchExplore = (query: string) => getJson<Exploration>(`${BASE}explore/?${query}`);
export const fetchPresets = () => getJson<Preset[]>(`${BASE}presets/`);
export const fetchPayEquity = (query: string) =>
  getJson<PayEquity>(`${BASE}pay-equity/?${query}`);
