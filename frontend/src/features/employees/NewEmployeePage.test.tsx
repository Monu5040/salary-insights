import { fireEvent, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { ASHA, json, lastSent, REFERENCE, stubApi } from "../../test/api";
import { choose } from "../../test/antd";
import { renderApp } from "../../test/renderApp";

function stubNew(answer: () => Response) {
  return stubApi({
    ...REFERENCE,
    "POST /api/v1/employees/": answer,
    "GET /api/v1/employees/7/": () => json(ASHA),
  });
}

/** Set a text field in one go; typing it key by key is slow in jsdom and tests nothing more. */
const enter = (label: string, value: string) =>
  fireEvent.change(screen.getByLabelText(label), { target: { value } });

async function fillIn() {
  await screen.findByLabelText("Employee code");
  enter("Employee code", "e00007");
  enter("Full name", "Asha Rao");
  enter("Work email", "asha.rao@acme.example");
  await choose("Country", "India");
  await choose("Department", "Engineering");
  enter("Job title", "Data Analyst");
  enter("Hire date", "2026-10-01");
  enter("Annual base salary", "1800000");
}

describe("Add an employee", () => {
  it("saves the employee with their salary, then opens their page", async () => {
    const api = stubNew(() => json(ASHA, 201));
    renderApp("/employees/new");

    await fillIn();
    await userEvent.click(screen.getByRole("button", { name: "Add employee" }));

    expect(await screen.findByRole("heading", { name: "Asha Rao" })).toBeInTheDocument();
    expect(lastSent(api, "POST").body).toEqual({
      employee_code: "e00007",
      full_name: "Asha Rao",
      email: "asha.rao@acme.example",
      country: "IN",
      department: 1,
      job_title: "Data Analyst",
      hire_date: "2026-10-01",
      salary: "1800000",
      currency: "INR",
    });
  });

  it("uses the country's currency until another is picked, and points out the difference", async () => {
    stubNew(() => json(ASHA, 201));
    renderApp("/employees/new");

    await choose("Country", "India");
    expect(await screen.findByTitle("INR Indian rupee")).toBeInTheDocument();

    await choose("Currency", "USD US dollar");
    expect(
      await screen.findByText("Paid in USD, not INR, the usual currency in India."),
    ).toBeInTheDocument();
  });

  it("shows the server's field errors under their fields", async () => {
    const answer = () =>
      json(
        {
          status: 400,
          detail: "Some fields need attention.",
          errors: { salary: ["This currency allows at most 2 decimal places."] },
        },
        400,
      );
    stubNew(answer);
    renderApp("/employees/new");

    await fillIn();
    await userEvent.click(screen.getByRole("button", { name: "Add employee" }));

    expect(
      await screen.findByText("This currency allows at most 2 decimal places."),
    ).toBeInTheDocument();
  });

  it("links to the employee who already has the code", async () => {
    const answer = () =>
      json(
        {
          status: 409,
          detail: "Another employee already has this employee code.",
          errors: { employee_code: ["Another employee already has this employee code."] },
          existing_id: 7,
        },
        409,
      );
    stubNew(answer);
    renderApp("/employees/new");

    await fillIn();
    await userEvent.click(screen.getByRole("button", { name: "Add employee" }));

    expect(await screen.findByRole("link", { name: "Open that employee" })).toHaveAttribute(
      "href",
      "/employees/7",
    );
  });
});
