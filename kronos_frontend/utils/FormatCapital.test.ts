import { describe, expect, it } from "vitest";
import {
  formatCapital,
  formatCapitalString,
  formatCapitalWithoutSymbol,
} from "./FormatCapital";

// These assertions were written against the ORIGINAL three-function
// implementation (pre-refactor) and must stay green after deduplication.

describe("formatCapital", () => {
  it("formats zero", () => {
    expect(formatCapital(0)).toBe("$ 0");
  });

  it("passes small values through untouched", () => {
    expect(formatCapital(1)).toBe("$ 1");
    expect(formatCapital(999)).toBe("$ 999");
    expect(formatCapital(999.5)).toBe("$ 999.5");
  });

  it("formats negatives with a leading minus after the symbol", () => {
    expect(formatCapital(-1)).toBe("$ -1");
    expect(formatCapital(-500.25)).toBe("$ -500.25");
    expect(formatCapital(-1500)).toBe("$ -1k");
    expect(formatCapital(-250000)).toBe("$ -2.5L");
    expect(formatCapital(-20000000)).toBe("$ -2Cr");
  });

  it("floors thousands below one lakh", () => {
    expect(formatCapital(1000)).toBe("$ 1k");
    expect(formatCapital(1999)).toBe("$ 1k"); // floor, not round
    expect(formatCapital(99999)).toBe("$ 99k");
  });

  it("formats lakhs from 1e5 up to (not including) 1e7", () => {
    expect(formatCapital(100000)).toBe("$ 1L");
    expect(formatCapital(150000)).toBe("$ 1.5L");
    expect(formatCapital(123456)).toBe("$ 1.23L"); // 2dp, trailing zeros trimmed
    expect(formatCapital(9999999)).toBe("$ 100L"); // 99.99999 → toFixed(2) → 100
  });

  it("formats crores from 1e7 upward", () => {
    expect(formatCapital(10000000)).toBe("$ 1Cr");
    expect(formatCapital(12500000)).toBe("$ 1.25Cr");
    expect(formatCapital(1234567890)).toBe("$ 123.46Cr");
  });

  it("renders non-finite input as zero", () => {
    expect(formatCapital(NaN)).toBe("$ 0");
    expect(formatCapital(Infinity)).toBe("$ 0");
    expect(formatCapital(-Infinity)).toBe("$ 0");
  });
});

describe("formatCapitalWithoutSymbol", () => {
  it("matches formatCapital minus the currency prefix", () => {
    const cases = [
      0, 1, 999.5, -500.25, 1000, 1999, 99999, 100000, 150000, 9999999,
      10000000, 12500000, -1500, -250000, -20000000, NaN, Infinity,
    ];
    for (const c of cases) {
      expect(`$ ${formatCapitalWithoutSymbol(c)}`).toBe(formatCapital(c));
    }
  });

  it("spot-checks representative values", () => {
    expect(formatCapitalWithoutSymbol(0)).toBe("0");
    expect(formatCapitalWithoutSymbol(-42)).toBe("-42");
    expect(formatCapitalWithoutSymbol(55000)).toBe("55k");
    expect(formatCapitalWithoutSymbol(250000)).toBe("2.5L");
    expect(formatCapitalWithoutSymbol(30000000)).toBe("3Cr");
    expect(formatCapitalWithoutSymbol(NaN)).toBe("0");
  });
});

describe("formatCapitalString", () => {
  it("behaves as formatCapital(Number(input))", () => {
    const cases = [
      "0",
      "1",
      "999.5",
      "-500.25",
      "1000",
      "99999",
      "150000",
      "12500000",
      "-20000000",
    ];
    for (const c of cases) {
      expect(formatCapitalString(c)).toBe(formatCapital(Number(c)));
    }
  });

  it("spot-checks representative strings", () => {
    expect(formatCapitalString("0")).toBe("$ 0");
    expect(formatCapitalString("-750")).toBe("$ -750");
    expect(formatCapitalString("55000")).toBe("$ 55k");
    expect(formatCapitalString("250000")).toBe("$ 2.5L");
    expect(formatCapitalString("30000000")).toBe("$ 3Cr");
  });

  it("renders non-numeric strings as zero", () => {
    expect(formatCapitalString("abc")).toBe("$ 0");
    expect(formatCapitalString("")).toBe("$ 0"); // Number("") === 0
  });
});
