import { getJson } from "./http";

/** What every number in an answer is relative to (design §4). */
export type Answer = {
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
