import { test as base, expect } from "@playwright/test";

/**
 * Every test fails on an error in the browser's console or an uncaught exception, which is
 * also where a Content Security Policy violation shows (edge case #29). Chrome reports each
 * 4xx or 5xx response there too; those are the app's business, so they are left out.
 */
export const test = base.extend<{ browserErrors: string[] }>({
  browserErrors: [
    async ({ page }, use) => {
      const errors: string[] = [];
      page.on("console", (message) => {
        if (message.type() === "error" && !message.text().startsWith("Failed to load resource")) {
          errors.push(message.text());
        }
      });
      page.on("pageerror", (error) => errors.push(error.message));
      await use(errors);
      expect(errors, "errors in the browser").toEqual([]);
    },
    { auto: true },
  ],
});

export { expect };
