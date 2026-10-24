import { expect, test } from "./fixtures";

// Charts whose rows carry words of different lengths beside their bars: medians with and
// without cents, payrolls in millions and in hundreds.
const CHARTS = ["Payroll by country", "Payroll by department", "Salary ranges by country"];

test("every bar in a chart is drawn to one scale, however long the words beside it", async ({
  page,
}) => {
  await page.goto("/insights");

  for (const title of CHARTS) {
    const card = page.locator(".ant-card").filter({ has: page.getByRole("heading", { name: title }) });
    const tracks = card.getByRole("listitem").locator(':scope > [aria-hidden="true"]');
    await expect(tracks.first()).toBeVisible();
    const widths = await tracks.evaluateAll((elements) =>
      elements.map((element) => Math.round(element.getBoundingClientRect().width)),
    );

    expect(widths.length, title).toBeGreaterThan(1);
    expect(new Set(widths).size, `${title}: track widths ${widths.join(", ")}`).toBe(1);
  }
});

test("the headline counts all 10,000 seeded employees", async ({ page }) => {
  await page.goto("/insights");

  const headcount = page
    .locator(".ant-card")
    .filter({ has: page.locator(".ant-statistic-title", { hasText: "Headcount" }) });
  await expect(headcount).toContainText(/10,00\d/); // the seed, give or take one a browser test adds
});
