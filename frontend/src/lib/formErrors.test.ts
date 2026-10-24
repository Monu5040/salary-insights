import { describe, expect, it } from "vitest";

import { toFieldErrors } from "./formErrors";

describe("toFieldErrors", () => {
  it("puts nested errors under nested fields", () => {
    const errors = { email: ["Taken."], salary: { amount: ["Too many decimals."] } };

    expect(toFieldErrors(errors)).toEqual([
      { name: ["email"], errors: ["Taken."] },
      { name: ["salary", "amount"], errors: ["Too many decimals."] },
    ]);
  });
});
