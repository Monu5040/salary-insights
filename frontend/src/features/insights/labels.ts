import type { Dimension, Metric } from "../../api/insights";

export const METRICS: Record<Metric, string> = {
  headcount: "Headcount",
  payroll: "Payroll",
  mean: "Mean salary",
  median: "Median salary",
  p10: "P10",
  p25: "P25",
  p75: "P75",
  p90: "P90",
  min: "Lowest salary",
  max: "Highest salary",
};

export const DIMENSIONS: Record<Dimension, string> = {
  country: "Country",
  department: "Department",
  title: "Job title",
  tenure: "Years employed",
};
