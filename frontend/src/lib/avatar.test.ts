import { describe, expect, it } from "vitest";

import { avatarColours, initials } from "./avatar";

describe("initials", () => {
  it("takes the first letters of the first and last names", () => {
    expect(initials("Asha Rao")).toBe("AR");
    expect(initials("Luiz Felipe Dias")).toBe("LD");
    expect(initials("  grace   o'neill ")).toBe("GO");
  });

  it("copes with one name, letters outside A–Z, and nothing at all", () => {
    expect(initials("Madonna")).toBe("M");
    expect(initials("Élodie Ünal")).toBe("ÉÜ");
    expect(initials("")).toBe("");
  });
});

describe("avatarColours", () => {
  it("gives a name the same colours every time, and other names others", () => {
    expect(avatarColours("Asha Rao")).toEqual(avatarColours("Asha Rao"));
    const names = ["Asha Rao", "Dev Patel", "Ana Lima", "John Moore", "Julie Jones", "Wei Chen"];
    expect(new Set(names.map((name) => avatarColours(name).join())).size).toBeGreaterThan(1);
  });
});
