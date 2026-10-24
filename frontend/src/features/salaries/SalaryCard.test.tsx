import { fireEvent, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import type { SalaryHistory } from "../../api/employees";
import { ASHA, json, lastSent, problem, REFERENCE, requested, stubApi } from "../../test/api";
import { choose } from "../../test/antd";
import { renderApp } from "../../test/renderApp";

const PEERS = {
  currency: "INR",
  definition: "Same job title, every country",
  peers: 3,
  low_sample: true,
  pay: "1800000.00",
  p10: null,
  p25: null,
  median: null,
  p75: null,
  p90: null,
  percentile_rank: null,
  compa_ratio: null,
};

const HIRE = {
  id: 1,
  effective_date: "2024-01-15",
  amount: "1800000.00",
  currency: "INR",
  reason: "hire" as const,
  note: "",
  raise_percent: null,
  currency_change: false,
  scheduled: false,
};

const HISTORY: SalaryHistory = {
  employee_version: 3,
  current_id: 2,
  records: [
    {
      ...HIRE,
      id: 3,
      effective_date: "2027-04-01",
      amount: "2000000.00",
      reason: "merit",
      raise_percent: "3.84",
      scheduled: true,
    },
    {
      ...HIRE,
      id: 2,
      effective_date: "2025-04-01",
      amount: "1926000.00",
      reason: "promotion",
      note: "Team lead",
      raise_percent: "7.00",
    },
    HIRE,
  ],
};

const SAVED: SalaryHistory = { ...HISTORY, employee_version: 4 };

function stubSalary(routes: Record<string, () => Response> = {}) {
  return stubApi({
    ...REFERENCE,
    "GET /api/v1/employees/7/": () => json(ASHA),
    "GET /api/v1/employees/7/peers/": () => json(PEERS),
    "GET /api/v1/employees/7/salaries/": () => json(HISTORY),
    ...routes,
  });
}

async function card() {
  renderApp("/employees/7");
  const title = await screen.findByRole("heading", { name: "Salary" });
  const salary = title.closest(".ant-card") as HTMLElement;
  await within(salary).findByText("Starting salary"); // the history has loaded
  return salary;
}

async function openRecord() {
  const salary = await card();
  await userEvent.click(within(salary).getByRole("button", { name: "Record a change" }));
  return screen.findByRole("dialog");
}

describe("Salary history", () => {
  it("shows the salary in force and every change, newest first, with its raise", async () => {
    stubSalary();
    const salary = await card();

    expect(within(salary).getAllByText("₹19,26,000")).not.toHaveLength(0);
    const rows = within(salary).getAllByRole("row").slice(1);
    expect(rows[0]).toHaveTextContent("Scheduled");
    expect(rows[0]).toHaveTextContent("+3.84%");
    expect(rows[1]).toHaveTextContent("Current");
    expect(rows[1]).toHaveTextContent("Promotion · Team lead");
    expect(rows[2]).toHaveTextContent("Starting salary");
  });

  it("can't remove the starting salary, only correct it", async () => {
    stubSalary();
    const salary = await card();

    const rows = within(salary).getAllByRole("row").slice(1);
    expect(within(rows[1]).getByRole("button", { name: "Remove" })).toBeInTheDocument();
    expect(within(rows[2]).queryByRole("button", { name: "Remove" })).not.toBeInTheDocument();
    expect(within(rows[2]).getByRole("button", { name: "Correct" })).toBeInTheDocument();
  });
});

describe("Recording a change", () => {
  it("turns a raise in % into the exact amount, previews it and sends only the amount", async () => {
    const api = stubSalary({ "POST /api/v1/employees/7/salaries/": () => json(SAVED, 201) });
    const dialog = await openRecord();

    fireEvent.change(within(dialog).getByLabelText("Takes effect on"), {
      target: { value: "2026-10-01" },
    });
    fireEvent.change(within(dialog).getByLabelText("Raise (%)"), { target: { value: "10" } });

    // From the salary in force before that day: the promotion of April 2025.
    expect(
      await within(dialog).findByText("₹19,26,000 → ₹21,18,600 (+10.0%)"),
    ).toBeInTheDocument();
    await userEvent.click(within(dialog).getByRole("button", { name: "Save change" }));

    await screen.findByRole("button", { name: "Record a change" });
    const { body, headers } = lastSent(api, "POST");
    expect(body).toEqual({
      effective_date: "2026-10-01",
      amount: "2118600.00",
      currency: "INR",
      reason: "merit",
      note: "",
    });
    expect(headers).toMatchObject({ "If-Match": '"3"' });
  });

  it("can be back-dated, and refetches the record and peers once saved", async () => {
    const api = stubSalary({ "POST /api/v1/employees/7/salaries/": () => json(SAVED, 201) });
    const dialog = await openRecord();

    fireEvent.change(within(dialog).getByLabelText("Takes effect on"), {
      target: { value: "2024-06-01" },
    });
    fireEvent.change(within(dialog).getByLabelText("Raise (%)"), { target: { value: "2" } });
    expect(
      await within(dialog).findByText("₹18,00,000 → ₹18,36,000 (+2.0%)"),
    ).toBeInTheDocument();
    await choose("Reason", "Market adjustment");
    await userEvent.click(within(dialog).getByRole("button", { name: "Save change" }));

    await screen.findByRole("button", { name: "Record a change" });
    expect(lastSent(api, "POST").body).toMatchObject({ reason: "market", amount: "1836000.00" });
    const record = requested(api).filter((url) => url === "/api/v1/employees/7/");
    expect(record.length).toBeGreaterThan(1);
  });

  it("takes a new amount in another currency, where a % makes no sense", async () => {
    const api = stubSalary({ "POST /api/v1/employees/7/salaries/": () => json(SAVED, 201) });
    const dialog = await openRecord();

    await choose("Currency", "USD US dollar");
    fireEvent.change(within(dialog).getByLabelText("New salary (a year)"), {
      target: { value: "25000" },
    });

    expect(
      await within(dialog).findByText(/₹19,26,000 → \$25,000 \(a currency change/),
    ).toBeInTheDocument();
    await userEvent.click(within(dialog).getByRole("button", { name: "Save change" }));

    await screen.findByRole("button", { name: "Record a change" });
    expect(lastSent(api, "POST").body).toMatchObject({ amount: "25000", currency: "USD" });
  });

  it("offers to reload when someone else changed the employee first", async () => {
    stubSalary({
      "POST /api/v1/employees/7/salaries/": () =>
        problem(412, "Someone else changed this employee since you opened it."),
    });
    const dialog = await openRecord();

    fireEvent.change(within(dialog).getByLabelText("Raise (%)"), { target: { value: "5" } });
    await userEvent.click(within(dialog).getByRole("button", { name: "Save change" }));

    expect(
      await within(dialog).findByText("Someone else changed this employee while you were working."),
    ).toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: "Reload" })).toBeInTheDocument();
  });

  it("can't save until the amount makes sense", async () => {
    stubSalary();
    const dialog = await openRecord();

    expect(within(dialog).getByRole("button", { name: "Save change" })).toBeDisabled();
    fireEvent.change(within(dialog).getByLabelText("Raise (%)"), { target: { value: "-100" } });
    expect(within(dialog).getByRole("button", { name: "Save change" })).toBeDisabled();
  });
});

describe("Correcting and removing", () => {
  it("corrects an amount with the version on screen", async () => {
    const api = stubSalary({ "PATCH /api/v1/employees/7/salaries/2/": () => json(SAVED) });
    const salary = await card();
    const promotion = within(salary).getAllByRole("row")[2];

    await userEvent.click(within(promotion).getByRole("button", { name: "Correct" }));
    const dialog = await screen.findByRole("dialog");
    fireEvent.change(within(dialog).getByLabelText("Salary (a year)"), {
      target: { value: "1930000" },
    });
    await userEvent.click(within(dialog).getByRole("button", { name: "Save correction" }));

    await screen.findByRole("button", { name: "Record a change" });
    const { body, headers } = lastSent(api, "PATCH");
    expect(body).toMatchObject({ amount: "1930000", effective_date: "2025-04-01" });
    expect(headers).toMatchObject({ "If-Match": '"3"' });
  });

  it("keeps the starting salary on the hire date", async () => {
    stubSalary();
    const salary = await card();
    const hire = within(salary).getAllByRole("row")[3];

    await userEvent.click(within(hire).getByRole("button", { name: "Correct" }));
    const dialog = await screen.findByRole("dialog");

    expect(within(dialog).getByLabelText("Takes effect on")).toBeDisabled();
  });

  it("removes a change after asking", async () => {
    const api = stubSalary({ "DELETE /api/v1/employees/7/salaries/3/": () => json(SAVED) });
    const salary = await card();
    const scheduled = within(salary).getAllByRole("row")[1];

    await userEvent.click(within(scheduled).getByRole("button", { name: "Remove" }));
    const confirm = (await screen.findByText("Remove this change?")).closest(
      ".ant-popover",
    ) as HTMLElement;
    await userEvent.click(within(confirm).getByRole("button", { name: "Remove" }));

    expect(requested(api, "DELETE")).toEqual(["/api/v1/employees/7/salaries/3/"]);
  });
});

describe("Among peers", () => {
  it("warns when the group is small and says which group was used", async () => {
    stubSalary();
    renderApp("/employees/7");

    expect(await screen.findByText("Same job title, every country: 3 people")).toBeInTheDocument();
    expect(screen.getByText("Fewer than 5: read with care")).toBeInTheDocument();
  });

  it("explains that someone starting later has no peers to compare yet", async () => {
    stubSalary({
      "GET /api/v1/employees/7/peers/": () =>
        problem(404, "This employee has no salary yet: their first one starts later."),
    });
    renderApp("/employees/7");

    expect(
      await screen.findByText("This employee has no salary yet: their first one starts later."),
    ).toBeInTheDocument();
  });
});
