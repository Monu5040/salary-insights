import type { Page } from "@playwright/test";

import { expect, test } from "./fixtures";

const HEADER =
  "employee_code,full_name,email,country,department,job_title," +
  "hire_date,salary,currency,effective_date,reason";

/** The preview's card, titled "What <file> changes". */
const card = (page: Page) =>
  page.locator(".ant-card").filter({ has: page.getByRole("heading", { name: /changes$/ }) });

test("an exported sheet imports back with nothing to change", async ({ page }) => {
  const sheet = await page.request.get("/api/v1/exports/employees.csv?country=JP");
  expect(sheet.headers()["content-type"]).toContain("text/csv");

  await page.goto("/import");
  await page
    .locator("input[type=file]")
    .setInputFiles({ name: "japan.csv", mimeType: "text/csv", buffer: await sheet.body() });
  await page.getByRole("button", { name: "Preview" }).click();

  await expect(card(page).getByRole("tab", { name: "Changes (0)" })).toBeVisible();
  await expect(card(page).getByRole("tab", { name: "New (0)" })).toBeVisible();
  await expect(card(page).getByRole("button", { name: "Apply" })).toBeDisabled();
});

test("a sheet adding an employee is previewed, applied, then found", async ({ page }) => {
  const row =
    "BT-0100,Imogen Import,imogen.test@acme.example,GB,Legal,Legal Counsel," +
    "15/03/2026,82000,GBP,15/03/2026,";
  await page.goto("/import");
  await page.locator("input[type=file]").setInputFiles({
    name: "new-starter.csv",
    mimeType: "text/csv",
    buffer: Buffer.from(`${HEADER}\n${row}\n`),
  });
  await page.getByLabel("Day first (31/12/2026)").check();
  await page.getByRole("button", { name: "Preview" }).click();

  await expect(card(page).getByRole("tab", { name: "New (1)" })).toBeVisible();
  await card(page).getByRole("button", { name: "Apply" }).click();
  await page.getByRole("tooltip").getByRole("button", { name: "Apply" }).click();
  await expect(page.getByText("Imported new-starter.csv")).toBeVisible();

  await page.goto("/employees?q=BT-0100");
  await expect(page.getByRole("link", { name: "Imogen Import" })).toBeVisible();
  await expect(page.getByRole("row").filter({ hasText: "Imogen Import" })).toContainText("82,000");
});
