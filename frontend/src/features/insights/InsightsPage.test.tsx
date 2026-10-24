import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import type { Exploration, Group, Preset } from "../../api/insights";
import { json, problem, REFERENCE, requested, stubApi } from "../../test/api";
import { choose } from "../../test/antd";
import { renderApp } from "../../test/renderApp";

// The hand-computed company of the backend's insights tests, as the API answers for it.
const ANSWER = {
  currency: "USD",
  fx_basis: "Converted through USD at fixed budget exchange rates",
};

const SUMMARY = {
  ...ANSWER,
  headcount: 6,
  payroll: "358000.00",
  median: "57500.00",
  mean: "59666.67",
};

const PRESETS: Preset[] = [
  {
    id: "payroll-by-country",
    title: "Payroll by country",
    chart: "bars",
    metrics: ["payroll"],
    by: ["country"],
  },
  {
    id: "ranges-by-department",
    title: "Salary ranges by department",
    chart: "ranges",
    metrics: ["p10", "p25", "median", "p75", "p90"],
    by: ["department"],
  },
  {
    id: "salary-by-job-title",
    title: "Salary by job title",
    chart: "table",
    metrics: ["headcount", "min", "median", "mean", "max"],
    by: ["title"],
  },
];

const group = (labels: Group["labels"], n: number, values: Group["values"]): Group => ({
  keys: labels,
  labels,
  headcount: n,
  low_sample: n < 5,
  values,
});

const TITLES = Array.from({ length: 14 }, (_, index) =>
  group({ title: `Title ${String(index + 1).padStart(2, "0")}` }, 6, {
    headcount: "6",
    min: "20000.00",
    median: `${30000 + index * 1000}.00`,
    mean: "35000.00",
    max: "50000.00",
  }),
);

/** The explorer's answer for a query, like the backend's for the company above. */
function explore(url = ""): Exploration {
  const query = new URLSearchParams(url.split("?")[1]);
  const by = query.getAll("by").filter(Boolean) as Exploration["by"];
  const metrics = query.getAll("metric") as Exploration["metrics"];
  const groups: Record<string, Group[]> = {
    country: [
      group({ country: "India" }, 4, { payroll: "168000.00", median: "38000.00" }),
      group({ country: "United States" }, 2, { payroll: "190000.00", median: "95000.00" }),
    ],
    department: [
      group({ department: "Engineering" }, 3, {
        p10: "27600.00", p25: "34500.00", median: "46000.00", p75: "68000.00", p90: "81200.00",
      }),
      group({ department: "Sales" }, 3, {
        p10: "37800.00", p25: "49500.00", median: "69000.00", p75: "84500.00", p90: "93800.00",
      }),
    ],
    title: TITLES,
  };
  return { ...ANSWER, metrics, by, groups: groups[by.join(",")] ?? [] };
}

function stub(overrides: Record<string, () => Response> = {}) {
  return stubApi({
    ...REFERENCE,
    "GET /api/v1/analytics/summary/": () => json(SUMMARY),
    "GET /api/v1/analytics/presets/": () => json(PRESETS),
    "GET /api/v1/analytics/explore/": (_init, url) => json(explore(url)),
    ...overrides,
  });
}

const card = async (title: string) =>
  (await screen.findByText(title)).closest(".ant-card") as HTMLElement;

describe("Insights", () => {
  it("shows headcount, payroll and the median and mean salary, and how they were converted", async () => {
    stub();
    renderApp("/insights");

    expect(await screen.findByText("$358K")).toBeInTheDocument();
    const median = screen.getByText("Median salary", { selector: ".ant-statistic-title" })
      .closest(".ant-card");
    expect(median).toHaveTextContent("$57,500");
    expect(median).toHaveTextContent("Mean $59,666.67");
    expect(
      screen.getByText(/Converted through USD at fixed budget exchange rates/),
    ).toBeInTheDocument();
  });

  it("answers the dashboard's questions", async () => {
    stub();
    renderApp("/insights");

    const payroll = await card("Payroll by country");
    expect(await within(payroll).findByText("India")).toBeInTheDocument();
    expect(within(payroll).getByText("$168K")).toBeInTheDocument();
    expect(within(payroll).getByText("4 people")).toBeInTheDocument();

    const ranges = await card("Salary ranges by department");
    expect(await within(ranges).findByText("median $46,000")).toBeInTheDocument();
    expect(within(ranges).getAllByText("Under 5 people")).toHaveLength(2);
  });

  it("pages through every job title, sorted as asked", async () => {
    stub();
    renderApp("/insights");

    const titles = await card("Salary by job title");
    expect(await within(titles).findByText("Title 01")).toBeInTheDocument();
    expect(within(titles).queryByText("Title 11")).not.toBeInTheDocument(); // on page 2

    await userEvent.click(within(titles).getByRole("columnheader", { name: /Median salary/ }));
    await userEvent.click(within(titles).getByRole("columnheader", { name: /Median salary/ }));

    const rows = within(titles).getAllByRole("row");
    expect(rows[1]).toHaveTextContent("Title 14"); // the highest median first
  });

  it("asks every insight again in the currency chosen", async () => {
    const api = stub();
    renderApp("/insights");
    await screen.findByText("$358K");

    await choose("Currency", "INR Indian rupee");

    await screen.findByText("$358K");
    const asked = requested(api).filter(
      (url) => url.startsWith("/api/v1/analytics/") && !url.includes("presets"),
    );
    const latest = new Map(asked.map((url) => [url.split("?")[0], url]));
    expect([...latest.values()].every((url) => url.includes("currency=INR"))).toBe(true);
    expect(latest.size).toBe(2); // summary and explore
  });

  it("filters by country and department, and nothing else", async () => {
    const api = stub();
    renderApp("/insights?country=IN&level=L3&as_of=2025-01-01");
    await screen.findByText("$358K");

    const summary = requested(api).filter((url) => url.startsWith("/api/v1/analytics/summary/"));
    expect(summary.at(-1)).toBe("/api/v1/analytics/summary/?country=IN");
  });

  it("keeps the explorer's choices in the page address", async () => {
    const api = stub();
    renderApp("/insights");
    await screen.findByText("Explore");

    await choose("Group by", "Job title");

    const explored = requested(api).filter((url) => url.startsWith("/api/v1/analytics/explore/"));
    expect(explored.at(-1)).toBe("/api/v1/analytics/explore/?metric=median&by=country&by=title");
  });

  it("explains an unknown currency instead of showing nothing", async () => {
    const missing = () => problem(422, "No exchange rate for XYZ.");
    stub({ "GET /api/v1/analytics/summary/": missing });
    renderApp("/insights?currency=XYZ");

    expect(await screen.findByText("No exchange rate for XYZ.")).toBeInTheDocument();
  });
});
