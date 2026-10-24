import { describe, expect, it } from "vitest";

import vectors from "../../../shared/money-vectors.json";
import { applyRaise, formatMoney, isAmount, raisePercent, roundToMinorUnit } from "./money";

// The same cases the backend's tests use, so a preview always equals what is saved.
describe("money, against the vectors shared with the backend", () => {
  it.each(vectors.round_to_minor_unit)(
    "rounds $amount to $minor_units decimals as $expected",
    ({ amount, minor_units, expected }) => {
      expect(roundToMinorUnit(amount, minor_units)).toBe(expected);
    },
  );

  it.each(vectors.apply_raise)(
    "$amount raised by $percent% is $expected",
    ({ amount, percent, minor_units, expected }) => {
      expect(applyRaise(amount, percent, minor_units)).toBe(expected);
    },
  );
});

describe("money", () => {
  it("stays exact where floating point wouldn't", () => {
    expect(0.1 + 0.2).not.toBe(0.3); // the reason for scaled integers
    expect(applyRaise("12345678901234.56", "10", 2)).toBe("13580246791358.02");
  });

  it("works out the raise to one decimal", () => {
    expect(raisePercent("1800000", "1926000.00")).toBe("7.0");
    expect(raisePercent("85000.00", "80750")).toBe("-5.0");
    expect(raisePercent("3", "4")).toBe("33.3");
  });

  it("knows a valid amount for a currency", () => {
    expect(isAmount("1926000.50", 2)).toBe(true);
    expect(isAmount("150000", 0)).toBe(true);
    expect(isAmount("150000.5", 0)).toBe(false);
    expect(isAmount("-5", 2)).toBe(false);
    expect(isAmount("1,800,000", 2)).toBe(false);
  });

  it("writes amounts the way each country does", () => {
    expect(formatMoney("1926000.00", "INR", "en-IN", 2)).toBe("₹19,26,000");
    expect(formatMoney("1926000.50", "INR", "en-IN", 2)).toBe("₹19,26,000.50");
    expect(formatMoney("150000", "JPY", "ja-JP", 0)).toBe("￥150,000");
    expect(formatMoney("1234.500", "KWD", "en-KW", 3)).toBe("KWD\u00a01,234.500"); // no-break space
  });
});
