import type { Page } from "@playwright/test";

import { expect, test } from "./fixtures";

/** Open an employee's page by id, and return their name from its heading. */
async function openEmployee(page: Page, id: number): Promise<string> {
  await page.goto(`/employees/${id}`);
  const heading = page.getByRole("heading", { level: 1 });
  await expect(page.getByRole("heading", { name: "Among peers" })).toBeVisible();
  return (await heading.textContent()) ?? "";
}

/** The employee's Salary card. */
const salaryCard = (page: Page) =>
  page
    .locator(".ant-card")
    .filter({ has: page.getByRole("heading", { name: "Salary", exact: true }) });

/** The salary in force today, as the Salary card shows it. */
const salaryShown = (page: Page) => salaryCard(page).locator("strong").first();

test("a raise from today shows on the employee and in the directory", async ({ page }) => {
  const name = await openEmployee(page, 33);
  const before = await salaryShown(page).textContent();

  await salaryCard(page).getByRole("button", { name: "Record a change" }).click();
  const dialog = page.getByRole("dialog", { name: "Record a salary change" });
  await dialog.getByLabel("Raise (%)").fill("4");
  await expect(dialog.getByText(/\(\+4\.0%\)/)).toBeVisible(); // the preview, before saving
  await dialog.getByRole("button", { name: "Save change" }).click();
  await expect(dialog).toBeHidden();

  const after = await salaryShown(page).textContent();
  expect(after).not.toBe(before);
  await page.getByRole("menuitem", { name: "Employees" }).click();
  await page.getByLabel("Search employees").fill("E00033");
  await page.getByLabel("Search employees").press("Enter");
  const row = page.getByRole("row").filter({ hasText: name });
  await expect(row).toContainText(after ?? "");
});

test("a back-dated raise takes its place in the history, then can be removed", async ({
  page,
}) => {
  await openEmployee(page, 34);

  await salaryCard(page).getByRole("button", { name: "Record a change" }).click();
  const dialog = page.getByRole("dialog", { name: "Record a salary change" });
  await dialog.getByLabel("Takes effect on").fill("2025-10-01");
  await dialog.getByLabel("Raise (%)").fill("2.5");
  await expect(dialog.getByText(/\(\+2\.5%\)/)).toBeVisible();
  await dialog.getByRole("button", { name: "Save change" }).click();
  await expect(dialog).toBeHidden();

  const row = salaryCard(page).getByRole("row").filter({ hasText: "1 Oct 2025" });
  await expect(row).toContainText("+2.50%");
  await row.getByRole("button", { name: "Remove" }).click();
  await page.getByRole("tooltip").getByRole("button", { name: "Remove" }).click();
  await expect(row).toHaveCount(0);
});

test("an employee can be added, then deleted", async ({ page }) => {
  await page.goto("/employees/new");
  await page.getByLabel("Employee code").fill("E2E-0001");
  await page.getByLabel("Full name").fill("Dana Example");
  await page.getByLabel("Work email").fill("dana.e2e@acme.example");
  await page.getByRole("combobox", { name: "Country" }).click();
  await page.getByTitle("Germany").click();
  await page.getByRole("combobox", { name: "Department" }).click();
  await page.getByTitle("Finance").click();
  await page.getByLabel("Job title").fill("Financial Analyst");
  await page.getByLabel("Hire date").fill("2026-10-01");
  await page.getByLabel("Annual base salary").fill("72000");
  await page.getByRole("button", { name: "Add employee" }).click();

  await expect(page.getByRole("heading", { level: 1, name: "Dana Example" })).toBeVisible();
  await expect(salaryShown(page)).toHaveText(/^72\.000\s€$/); // in EUR, as Germany writes it

  await page.getByRole("button", { name: "Delete" }).click();
  await page.getByRole("tooltip").getByRole("button", { name: "Delete" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Employees" })).toBeVisible();
  await page.goto("/employees?q=E2E-0001");
  await expect(page.getByText("No employees match these filters")).toBeVisible();
});

test("when someone else saved first, the save is refused and Reload shows theirs", async ({
  page,
  browser,
}) => {
  // Two HR managers open the same person, each in their own browser.
  const other = await browser.newPage();
  for (const tab of [page, other]) await openEmployee(tab, 35);

  await other.getByRole("button", { name: "Edit details" }).click();
  await other.getByLabel("Job title").fill("Software Engineer (e2e)");
  await other.getByRole("button", { name: "Save" }).click();
  await expect(other.getByRole("dialog")).toBeHidden();

  await page.getByRole("button", { name: "Edit details" }).click();
  await page.getByLabel("Job title").fill("Staff Engineer (e2e)");
  await page.getByRole("button", { name: "Save" }).click();
  await expect(
    page.getByText("Someone else changed this employee while you were working."),
  ).toBeVisible();
  await page.getByRole("button", { name: "Reload" }).click();

  await expect(page.getByLabel("Job title")).toHaveValue("Software Engineer (e2e)");
  await other.close();
});
