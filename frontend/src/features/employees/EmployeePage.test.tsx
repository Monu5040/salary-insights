import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import type { Employee } from "../../api/employees";
import { ASHA, json, lastSent, problem, REFERENCE, requested, stubApi } from "../../test/api";
import { renderApp } from "../../test/renderApp";

const PEERS = {
  currency: "INR",
  definition: "Same job title and country",
  peers: 12,
  low_sample: false,
  pay: "1800000.00",
  p10: "1500000.00",
  p25: "1650000.00",
  median: "2000000.00",
  p75: "2200000.00",
  p90: "2500000.00",
  percentile_rank: "25",
  compa_ratio: "0.90",
};

function stubEmployee(employee: Employee = ASHA, writes: Record<string, () => Response> = {}) {
  return stubApi({
    ...REFERENCE,
    [`GET /api/v1/employees/${employee.id}/`]: () => json(employee),
    [`GET /api/v1/employees/${employee.id}/peers/`]: () => json(PEERS),
    "GET /api/v1/employees/": () => json({ count: 0, page: 1, page_size: 25, results: [] }),
    ...writes,
  });
}

describe("Employee page", () => {
  it("shows the record, the salary and where it sits among peers", async () => {
    stubEmployee();
    renderApp("/employees/7");

    expect(await screen.findByRole("heading", { name: "Asha Rao" })).toBeInTheDocument();
    expect(screen.getByText("Data Analyst")).toBeInTheDocument();
    expect(screen.getByText("15 Jan 2024")).toBeInTheDocument();
    expect(await screen.findAllByText("₹18,00,000")).not.toHaveLength(0);
    expect(await screen.findByText("Same job title and country: 12 people")).toBeInTheDocument();
    expect(screen.getByText("25% of peers")).toBeInTheDocument();
    expect(screen.getByText("₹20,00,000")).toBeInTheDocument(); // the peer median
  });

  it("saves an edit with the version on screen, then shows the saved record", async () => {
    const api = stubEmployee(ASHA, {
      "PATCH /api/v1/employees/7/": () => json({ ...ASHA, job_title: "Lead Analyst", version: 4 }),
    });
    renderApp("/employees/7");
    await userEvent.click(await screen.findByRole("button", { name: "Edit details" }));

    const title = await screen.findByLabelText("Job title");
    await userEvent.clear(title);
    await userEvent.type(title, "Lead Analyst");
    await userEvent.click(screen.getByRole("button", { name: "Save" }));

    expect(await screen.findByText("Lead Analyst")).toBeInTheDocument();
    const { body, headers } = lastSent(api, "PATCH");
    expect(headers).toMatchObject({ "If-Match": '"3"' });
    expect(body).toMatchObject({ job_title: "Lead Analyst", country: "IN", department: 1 });
    expect(body).not.toHaveProperty("salary"); // the salary has its own form
  });

  it("on Reload after a clash, shows their record instead of what was typed", async () => {
    const theirs = { ...ASHA, job_title: "Senior Analyst", version: 4 };
    let onServer = ASHA;
    const api = stubEmployee(ASHA, {
      "GET /api/v1/employees/7/": () => json(onServer),
      "PATCH /api/v1/employees/7/": () => {
        onServer = theirs; // they saved just before us
        return problem(412, "Someone else changed this employee since you opened it.");
      },
    });
    renderApp("/employees/7");
    await userEvent.click(await screen.findByRole("button", { name: "Edit details" }));
    const title = await screen.findByLabelText("Job title");
    fireEvent.change(title, { target: { value: "Lead Analyst" } });
    await userEvent.click(screen.getByRole("button", { name: "Save" }));

    const warning = await screen.findByText(
      "Someone else changed this employee while you were working.",
    );
    await userEvent.click(screen.getByRole("button", { name: "Reload" }));

    await waitFor(() => expect(screen.getByLabelText("Job title")).toHaveValue("Senior Analyst"));
    expect(warning).not.toBeInTheDocument();
    const loads = requested(api).filter((url) => url === "/api/v1/employees/7/");
    expect(loads).toHaveLength(2);
  });

  it("deletes the employee after asking, then returns to the directory", async () => {
    const api = stubEmployee(ASHA, {
      "DELETE /api/v1/employees/7/": () => new Response(null, { status: 204 }),
    });
    renderApp("/employees/7");

    await userEvent.click(await screen.findByRole("button", { name: "Delete" }));
    const confirm = await screen.findByRole("tooltip");
    await userEvent.click(within(confirm).getByRole("button", { name: "Delete" }));

    expect(await screen.findByRole("heading", { name: "Employees" })).toBeInTheDocument();
    expect(lastSent(api, "DELETE").headers).toMatchObject({ "If-Match": '"3"' });
  });

  it("says so when there is no such employee", async () => {
    stubApi({ ...REFERENCE });
    renderApp("/employees/999");

    expect(await screen.findByText("No such employee")).toBeInTheDocument();
  });
});
