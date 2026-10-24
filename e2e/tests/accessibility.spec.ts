import AxeBuilder from "@axe-core/playwright";
import type { Page } from "@playwright/test";
import type { NodeResult } from "axe-core";

import { expect, test } from "./fixtures";

/** Each page once loaded: its address, and something on it that says it has finished. */
const PAGES = [
  { name: "Insights", path: "/insights", ready: "Salary by job title" },
  { name: "Employees", path: "/employees", ready: /^[\d,]+ employees$/ },
  { name: "An employee", path: "/employees/2", ready: "Among peers" },
  { name: "Add an employee", path: "/employees/new", ready: "Annual base salary" },
];

/**
 * Ant Design's Form.Item puts aria-required on a Select's outer box as well as on its combobox
 * input, and the box has no role to carry it. Screen readers ignore it there and read it from
 * the input, which a test below checks, so this one finding, and nothing else, is left out.
 */
const isSelectBoxRequired = (rule: string, node: NodeResult) =>
  rule === "aria-allowed-attr" &&
  node.html.startsWith('<div class="ant-select ') &&
  /^Fix all of the following:\s+ARIA attribute is not allowed: aria-required="true"$/.test(
    node.failureSummary ?? "",
  );

/** WCAG 2.2 A and AA, as axe checks them in a real browser, colour contrast included. */
async function violations(page: Page): Promise<string[]> {
  // Colours are measured at rest: a dialog still fading in reads as low contrast. Endless
  // animations (a spinner) never finish, and the ripple a button shows for two seconds after
  // a click is decoration, so neither is waited for.
  await page.waitForFunction(() =>
    document.getAnimations().every((animation) => {
      const target = (animation.effect as KeyframeEffect | null)?.target;
      return (
        animation.playState !== "running" ||
        animation.effect?.getTiming().iterations === Infinity ||
        Boolean(target?.classList.contains("ant-wave"))
      );
    }),
  );
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"])
    .analyze();
  return results.violations.flatMap((violation) => {
    const nodes = violation.nodes.filter((node) => !isSelectBoxRequired(violation.id, node));
    return nodes.map((node) => `${violation.id}: ${node.failureSummary} — ${node.html}`);
  });
}

for (const { name, path, ready } of PAGES) {
  test(`${name} is accessible`, async ({ page }) => {
    await page.goto(path);
    await expect(page.getByText(ready).first()).toBeVisible();
    // Every card and table has its answer, so everything on the page is checked.
    await expect(page.locator(".ant-card-loading, .ant-spin-spinning")).toHaveCount(0);

    expect(await violations(page)).toEqual([]);
  });
}

test("required fields say so to screen readers, lists included", async ({ page }) => {
  await page.goto("/employees/new");

  for (const name of ["Country", "Department", "Currency"]) {
    await expect(page.getByRole("combobox", { name })).toHaveAttribute("aria-required", "true");
  }
});

test("the dialogs for changing someone are accessible", async ({ page }) => {
  await page.goto("/employees/37");
  await expect(page.getByRole("heading", { name: "Among peers" })).toBeVisible();
  const name = await page.getByRole("heading", { level: 1 }).textContent();

  await page.getByRole("button", { name: "Change salary" }).click();
  await expect(page.getByRole("dialog", { name: "Change salary" })).toBeVisible();
  expect(await violations(page)).toEqual([]);
  await page.keyboard.press("Escape");

  await page.getByRole("button", { name: "Edit details" }).click();
  await expect(page.getByRole("dialog", { name: `Edit ${name}'s details` })).toBeVisible();
  expect(await violations(page)).toEqual([]);
});
