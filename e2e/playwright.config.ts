import { defineConfig, devices } from "@playwright/test";

// The built app, served by Django as in production: e2e/run.sh (`make e2e`) starts it.
export default defineConfig({
  testDir: "tests",
  // The tests share one database and some of them write, so they run one at a time.
  workers: 1,
  // A flaky end-to-end test is a bug to fix, not to retry.
  retries: 0,
  forbidOnly: Boolean(process.env.CI),
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://127.0.0.1:8300",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
