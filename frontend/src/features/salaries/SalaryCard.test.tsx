import { fireEvent, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { ASHA, json, lastSent, problem, REFERENCE, stubApi } from "../../test/api";
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

function stubSalary(patch: () => Response = () => json({ ...ASHA, version: 4 })) {
  return stubApi({
    ...REFERENCE,
    "GET /api/v1/employees/7/": () => json(ASHA),
    "GET /api/v1/employees/7/peers/": () => json(PEERS),
    "PATCH /api/v1/employees/7/": patch,
  });
}

async function openChange() {
  renderApp("/employees/7");
  await userEvent.click(await screen.findByRole("button", { name: "Change salary" }));
  return screen.findByRole("dialog");
}

describe("Changing a salary", () => {
  it("turns a raise in % into the exact amount, previews it and sends only the amount", async () => {
    const api = stubSalary(() => json({ ...ASHA, salary: "1926000.00", version: 4 }));
    const dialog = await openChange();

    fireEvent.change(within(dialog).getByLabelText("Raise (%)"), { target: { value: "7" } });

    expect(await within(dialog).findByText("₹18,00,000 → ₹19,26,000 (+7.0%)")).toBeInTheDocument();
    await userEvent.click(within(dialog).getByRole("button", { name: "Save salary" }));

    expect(await screen.findAllByText("₹19,26,000")).not.toHaveLength(0);
    const { body, headers } = lastSent(api, "PATCH");
    expect(body).toEqual({ salary: "1926000.00", currency: "INR" });
    expect(headers).toMatchObject({ "If-Match": '"3"' });
  });

  it("takes a new amount in another currency, where a % makes no sense", async () => {
    const api = stubSalary();
    const dialog = await openChange();

    await choose("Currency", "USD US dollar");
    fireEvent.change(within(dialog).getByLabelText("New annual salary"), {
      target: { value: "25000" },
    });

    expect(
      await within(dialog).findByText("₹18,00,000 → $25,000 (a change of currency)"),
    ).toBeInTheDocument();
    await userEvent.click(within(dialog).getByRole("button", { name: "Save salary" }));

    await screen.findByRole("button", { name: "Change salary" });
    expect(lastSent(api, "PATCH").body).toEqual({ salary: "25000", currency: "USD" });
  });

  it("offers to reload when someone else changed the employee first", async () => {
    stubSalary(() => problem(412, "Someone else changed this employee since you opened it."));
    const dialog = await openChange();

    fireEvent.change(within(dialog).getByLabelText("Raise (%)"), { target: { value: "5" } });
    await userEvent.click(within(dialog).getByRole("button", { name: "Save salary" }));

    expect(
      await within(dialog).findByText("Someone else changed this employee while you were working."),
    ).toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: "Reload" })).toBeInTheDocument();
  });

  it("can't save until the amount makes sense", async () => {
    stubSalary();
    const dialog = await openChange();

    expect(within(dialog).getByRole("button", { name: "Save salary" })).toBeDisabled();
    fireEvent.change(within(dialog).getByLabelText("Raise (%)"), { target: { value: "-100" } });
    expect(within(dialog).getByRole("button", { name: "Save salary" })).toBeDisabled();
  });
});

describe("Among peers", () => {
  it("warns when the group is small and says which group was used", async () => {
    stubSalary();
    renderApp("/employees/7");

    expect(await screen.findByText("Same job title, every country: 3 people")).toBeInTheDocument();
    expect(screen.getByText("Fewer than 5: read with care")).toBeInTheDocument();
  });
});
