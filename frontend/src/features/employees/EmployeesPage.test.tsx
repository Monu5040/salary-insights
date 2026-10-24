import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import type { EmployeeRow, Page } from "../../api/employees";
import { ASHA, json, REFERENCE, requested, stubApi } from "../../test/api";
import { renderApp } from "../../test/renderApp";

const BRUNO: EmployeeRow = {
  ...ASHA,
  id: 8,
  employee_code: "E00008",
  full_name: "Bruno Silva",
  country: { code: "US", name: "United States" },
  salary: "95000.00",
  currency: "USD",
};

function stubDirectory() {
  const page: Page<EmployeeRow> = { count: 2, page: 1, page_size: 25, results: [ASHA, BRUNO] };
  return stubApi({ ...REFERENCE, "GET /api/v1/employees/": () => json(page) });
}

const directoryCalls = (api: ReturnType<typeof stubApi>) =>
  requested(api).filter((url) => url.startsWith("/api/v1/employees/?"));

describe("Employee directory", () => {
  it("lists employees with their salary, as their country writes it, and the total", async () => {
    stubDirectory();
    renderApp("/employees");

    expect(await screen.findByRole("link", { name: "Asha Rao" })).toHaveAttribute(
      "href",
      "/employees/7",
    );
    expect(await screen.findByText("₹18,00,000")).toBeInTheDocument();
    expect(screen.getByText("$95,000")).toBeInTheDocument();
    expect(screen.getByText("2 employees")).toBeInTheDocument();
  });

  it("asks the API with the filters in the page's address, and only those", async () => {
    const api = stubDirectory();
    renderApp("/employees?department=1&country=IN&utm=mail&sort=-hire_date&page=2");

    await screen.findByText("Asha Rao");

    expect(directoryCalls(api)).toEqual([
      "/api/v1/employees/?country=IN&department=1&sort=-hire_date&page=2",
    ]);
  });

  it("searching puts the term in the address and starts again from page 1", async () => {
    const api = stubDirectory();
    renderApp("/employees?page=3");
    await screen.findByText("Asha Rao");

    await userEvent.type(screen.getByLabelText("Search employees"), "jose{Enter}");

    await screen.findByText("Asha Rao");
    expect(directoryCalls(api).at(-1)).toBe("/api/v1/employees/?q=jose");
  });

  it("sorts by a column, then the other way", async () => {
    const api = stubDirectory();
    renderApp("/employees");
    await screen.findByText("Asha Rao");

    await userEvent.click(screen.getByRole("columnheader", { name: /Hired/ }));
    expect(directoryCalls(api).at(-1)).toBe("/api/v1/employees/?sort=hire_date");

    await userEvent.click(screen.getByRole("columnheader", { name: /Hired/ }));
    expect(directoryCalls(api).at(-1)).toBe("/api/v1/employees/?sort=-hire_date");
  });

  it("adds an employee from the directory", async () => {
    stubDirectory();
    renderApp("/employees");
    await screen.findByText("Asha Rao");

    await userEvent.click(screen.getByRole("button", { name: "Add employee" }));

    expect(await screen.findByRole("heading", { name: "Add an employee" })).toBeInTheDocument();
  });

  it("has no export or status filter", async () => {
    stubDirectory();
    renderApp("/employees");
    await screen.findByText("Asha Rao");

    expect(screen.queryByRole("link", { name: "Export CSV" })).not.toBeInTheDocument();
    expect(screen.queryByText("Former")).not.toBeInTheDocument();
  });
});

describe("Employee directory, when there is nothing to show", () => {
  it("says when nobody matches, and clears the filters but keeps the sort", async () => {
    const api = stubApi({
      ...REFERENCE,
      "GET /api/v1/employees/": () => json({ count: 0, page: 1, page_size: 25, results: [] }),
    });
    renderApp("/employees?q=zzz&country=IN&sort=-hire_date");

    expect(await screen.findByText("No employees match these filters")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Clear filters" }));

    await waitFor(() =>
      expect(directoryCalls(api).at(-1)).toBe("/api/v1/employees/?sort=-hire_date"),
    );
  });

  it("gives the reference to quote when the server fails", async () => {
    stubApi({
      ...REFERENCE,
      "GET /api/v1/employees/": () =>
        json({ status: 500, detail: "Something went wrong on our side.", request_id: "a1b2c3d4" }, 500),
    });
    renderApp("/employees");

    expect(await screen.findByText("a1b2c3d4")).toBeInTheDocument();
    expect(screen.queryByText("No employees match these filters")).not.toBeInTheDocument();
  });
});
