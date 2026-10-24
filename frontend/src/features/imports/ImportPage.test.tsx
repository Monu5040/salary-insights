import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import type { ImportPreview } from "../../api/imports";
import { json, REFERENCE, stubApi } from "../../test/api";
import { renderApp } from "../../test/renderApp";

const CLEAN: ImportPreview = {
  rows: 2,
  creates: 1,
  changes: 1,
  unchanged: 0,
  error_rows: 0,
  ignored_columns: ["Notes"],
  new_employees: [
    {
      line: 2,
      employee_code: "E00777",
      full_name: "Asha Rao",
      salary: "1800000 INR from 2024-01-15 (hire)",
    },
  ],
  changed_employees: [
    {
      line: 3,
      employee_code: "E00001",
      full_name: "Bruno Silva",
      fields: { job_title: ["Engineer", "Staff Engineer"] },
      salary: null,
    },
  ],
  row_errors: [],
  fingerprint: "abc123",
};

const WITH_ERRORS: ImportPreview = {
  ...CLEAN,
  error_rows: 1,
  row_errors: [{ line: 3, column: "country", message: "No country with the code XX." }],
};

function sentForm(api: ReturnType<typeof stubApi>, path: string): FormData {
  const call = api.mock.calls.filter(([url]) => String(url) === path).at(-1);
  return call?.[1]?.body as FormData;
}

/** Pick a sheet, choose how its dates are written, and preview it. */
async function choose(dates?: string) {
  renderApp("/import");
  const input = (await screen.findByText("Click or drag a CSV file here"))
    .closest(".ant-upload")
    ?.querySelector("input[type=file]") as HTMLInputElement;
  await userEvent.upload(input, new File(["x"], "employees.csv", { type: "text/csv" }));
  if (dates) await userEvent.click(screen.getByLabelText(dates));
  await userEvent.click(screen.getByRole("button", { name: "Preview" }));
}

describe("Importing a sheet", () => {
  it("previews what it changes, with the date format chosen, and changes nothing", async () => {
    const api = stubApi({
      ...REFERENCE,
      "POST /api/v1/imports/preview/": () => json(CLEAN),
    });
    await choose("Day first (31/12/2026)");

    const review = (await screen.findByText("What employees.csv changes")).closest(
      ".ant-card",
    ) as HTMLElement;
    expect(within(review).getByText("Columns not imported: Notes.")).toBeInTheDocument();
    expect(within(review).getByText("job title: Engineer → Staff Engineer")).toBeInTheDocument();
    const form = sentForm(api, "/api/v1/imports/preview/");
    expect(form.get("date_format")).toBe("dmy");
    expect((form.get("file") as File).name).toBe("employees.csv");
  });

  it("won't apply a file with errors, and lists them", async () => {
    stubApi({ ...REFERENCE, "POST /api/v1/imports/preview/": () => json(WITH_ERRORS) });
    await choose();

    expect(await screen.findByText("No country with the code XX.")).toBeInTheDocument();
    expect(screen.getByText("1 row has errors")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Apply" })).toBeDisabled();
  });

  it("applies exactly the plan previewed, then says what changed", async () => {
    const api = stubApi({
      ...REFERENCE,
      "POST /api/v1/imports/preview/": () => json(CLEAN),
      "POST /api/v1/imports/apply/": () => json({ creates: 1, changes: 1, unchanged: 0 }),
    });
    await choose();

    await userEvent.click(await screen.findByRole("button", { name: "Apply" }));
    const confirm = (await screen.findByText("Apply this file?")).closest(
      ".ant-popover",
    ) as HTMLElement;
    await userEvent.click(within(confirm).getByRole("button", { name: "Apply" }));

    expect(await screen.findByText("Imported employees.csv")).toBeInTheDocument();
    expect(screen.getByText("1 new employees, 1 changed, 0 unchanged.")).toBeInTheDocument();
    expect(sentForm(api, "/api/v1/imports/apply/").get("fingerprint")).toBe("abc123");
  });

  it("shows the fresh preview when someone changed an employee in the file since", async () => {
    const fresh = { ...CLEAN, changes: 0, creates: 1, changed_employees: [], fingerprint: "def" };
    stubApi({
      ...REFERENCE,
      "POST /api/v1/imports/preview/": () => json(CLEAN),
      "POST /api/v1/imports/apply/": () =>
        json(
          {
            status: 409,
            detail: "Some employees in this file changed after the preview. Preview it again.",
            preview: fresh,
          },
          409,
        ),
    });
    await choose();

    await userEvent.click(await screen.findByRole("button", { name: "Apply" }));
    const confirm = (await screen.findByText("Apply this file?")).closest(
      ".ant-popover",
    ) as HTMLElement;
    await userEvent.click(within(confirm).getByRole("button", { name: "Apply" }));

    expect(
      await screen.findByText("Some employees in this file changed after the preview."),
    ).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Changes (0)" })).toBeInTheDocument();
  });
});
