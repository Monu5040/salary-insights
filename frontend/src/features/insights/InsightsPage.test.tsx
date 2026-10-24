import { fireEvent, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import type { Asked, Exploration, Group, PayEquity, Preset } from "../../api/insights";
import { json, lastSent, problem, REFERENCE, requested, stubApi } from "../../test/api";
import { choose } from "../../test/antd";
import { renderApp } from "../../test/renderApp";

// The hand-computed company of the backend's insights tests, as the API answers for it.
const ANSWER = {
  as_of: "2026-09-30",
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

// The backend's pay-equity answer for the company, with too few peers to need a band of 5.
const EQUITY: PayEquity = {
  ...ANSWER,
  band: ["0.80", "1.20"],
  count: 2,
  page: 1,
  page_size: 10,
  results: [
    {
      id: 5,
      employee_code: "T00005",
      full_name: "Hana",
      country_name: "United States",
      job_title: "Data Analyst",
      pay: "90000.00",
      peer_median: "34500.00",
      compa_ratio: "2.61",
      definition: "Same job title, every country",
      peers: 2,
    },
    {
      id: 1,
      employee_code: "T00001",
      full_name: "Ana",
      country_name: "India",
      job_title: "Data Analyst",
      pay: "23000.00",
      peer_median: "68000.00",
      compa_ratio: "0.34",
      definition: "Same job title, every country",
      peers: 2,
    },
  ],
};

type Route = Parameters<typeof stubApi>[0][string];

function stub(overrides: Record<string, Route> = {}) {
  return stubApi({
    ...REFERENCE,
    "GET /api/v1/analytics/summary/": () => json(SUMMARY),
    "GET /api/v1/analytics/presets/": () => json(PRESETS),
    "GET /api/v1/analytics/explore/": (_init, url) => json(explore(url)),
    "GET /api/v1/analytics/pay-equity/": () => json(EQUITY),
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
    expect(latest.size).toBe(3); // summary, pay equity and explore
  });

  it("filters by day, country and department, and nothing else", async () => {
    const api = stub();
    renderApp("/insights?country=IN&level=L3&as_of=2025-01-01");
    await screen.findByText("$358K");

    const summary = requested(api).filter((url) => url.startsWith("/api/v1/analytics/summary/"));
    expect(summary.at(-1)).toBe("/api/v1/analytics/summary/?as_of=2025-01-01&country=IN");
  });

  it("answers as of another day, and leaves today out of the address", async () => {
    const api = stub();
    renderApp("/insights");
    await screen.findByText("$358K");

    fireEvent.change(screen.getByLabelText("As of"), { target: { value: "2025-12-31" } });
    await screen.findByText("$358K");
    fireEvent.change(screen.getByLabelText("As of"), { target: { value: "2026-09-30" } });

    const summary = requested(api).filter((url) => url.startsWith("/api/v1/analytics/summary/"));
    expect(summary).toContain("/api/v1/analytics/summary/?as_of=2025-12-31");
    expect(summary.at(-1)).toBe("/api/v1/analytics/summary/?");
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

describe("Pay equity", () => {
  it("lists people far from others in the same role, each linked to their record", async () => {
    stub();
    renderApp("/insights");

    const equity = await card("Pay equity");
    expect(
      await within(equity).findByText(/below 80% or above 120% of the median/),
    ).toBeInTheDocument();
    const hana = within(equity).getByRole("link", { name: "Hana" });
    expect(hana).toHaveAttribute("href", "/employees/5");
    expect(within(equity).getByText("261%")).toBeInTheDocument();
    expect(within(equity).getByText("$34,500")).toBeInTheDocument();
  });
});

describe("Questions in plain English", () => {
  const ASKED: Asked = {
    question: "Payroll by country",
    summary: "Payroll by country, in USD.",
    query: { metric: ["payroll"], by: ["country"], country: [], department: [] },
    answer: explore("?metric=payroll&by=country"),
  };

  async function ask(question = "Payroll by country") {
    renderApp("/insights");
    const box = await screen.findByLabelText("Question");
    fireEvent.change(box, { target: { value: question } });
    await userEvent.click(screen.getByRole("button", { name: "Ask" }));
  }

  it("shows what the question was read as, and the answer", async () => {
    const api = stub({ "POST /api/v1/analytics/ask/": () => json(ASKED) });
    await ask();

    const box = await card("Ask a question");
    expect(await within(box).findByText("Payroll by country, in USD.")).toBeInTheDocument();
    expect(within(box).getByText("United States")).toBeInTheDocument();
    expect(lastSent(api, "POST").body).toEqual({ question: "Payroll by country" });
  });

  it("opens the reading in the explorer, to refine it there", async () => {
    const api = stub({ "POST /api/v1/analytics/ask/": () => json(ASKED) });
    await ask();
    const box = await card("Ask a question");

    await userEvent.click(await within(box).findByRole("button", { name: "Open in the explorer" }));

    const explored = requested(api).filter((url) => url.startsWith("/api/v1/analytics/explore/"));
    expect(explored.at(-1)).toBe("/api/v1/analytics/explore/?metric=payroll&by=country");
  });

  it("says why when a question can't be answered", async () => {
    stub({
      "POST /api/v1/analytics/ask/": () =>
        problem(422, "That question isn't one the explorer can answer."),
    });
    await ask("What's for lunch?");

    expect(
      await screen.findByText("That question isn't one the explorer can answer."),
    ).toBeInTheDocument();
  });

  it("asks people to wait when they ask too often", async () => {
    stub({ "POST /api/v1/analytics/ask/": () => problem(429, "Request was throttled.") });
    await ask();

    expect(await screen.findByText("Too many questions: wait a minute.")).toBeInTheDocument();
  });
});
