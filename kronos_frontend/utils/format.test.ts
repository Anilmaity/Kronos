import { describe, expect, it } from "vitest";
import {
  fmtDateTime,
  fmtNum,
  fmtNumber,
  fmtSigned,
  fmtTime,
  formatTime12h,
  pnlColor,
} from "./format";

describe("fmtNum", () => {
  it("formats numbers and numeric strings to fixed digits", () => {
    expect(fmtNum(1.2345)).toBe("1.23");
    expect(fmtNum("1.2345")).toBe("1.23");
    expect(fmtNum(1.2345, 4)).toBe("1.2345");
    expect(fmtNum(-2)).toBe("-2.00");
    expect(fmtNum(0)).toBe("0.00");
  });

  it("returns an em-dash for empty/invalid input", () => {
    expect(fmtNum(null)).toBe("—");
    expect(fmtNum(undefined)).toBe("—");
    expect(fmtNum("")).toBe("—");
    expect(fmtNum("abc")).toBe("—");
  });
});

describe("fmtSigned", () => {
  it("prefixes non-negative values with +", () => {
    expect(fmtSigned(1.5)).toBe("+1.50");
    expect(fmtSigned(0)).toBe("+0.00");
    expect(fmtSigned("68")).toBe("+68.00");
  });

  it("keeps the minus for negatives", () => {
    expect(fmtSigned(-3.259)).toBe("-3.26");
  });

  it("returns an em-dash for empty/invalid input", () => {
    expect(fmtSigned(null)).toBe("—");
    expect(fmtSigned("")).toBe("—");
    expect(fmtSigned("x")).toBe("—");
  });
});

describe("pnlColor", () => {
  it("is tv-down below zero and tv-up at or above zero", () => {
    expect(pnlColor(-0.01)).toBe("var(--tv-down)");
    expect(pnlColor(0)).toBe("var(--tv-up)");
    expect(pnlColor("12.5")).toBe("var(--tv-up)");
  });

  it("is soft for empty/invalid input", () => {
    expect(pnlColor(null)).toBe("var(--tv-text-soft)");
    expect(pnlColor(undefined)).toBe("var(--tv-text-soft)");
    expect(pnlColor("")).toBe("var(--tv-text-soft)");
    expect(pnlColor("abc")).toBe("var(--tv-text-soft)");
  });
});

describe("fmtTime", () => {
  it("returns an em-dash for empty input", () => {
    expect(fmtTime(null)).toBe("—");
    expect(fmtTime(undefined)).toBe("—");
    expect(fmtTime("")).toBe("—");
  });

  it("returns the raw input when unparseable", () => {
    expect(fmtTime("not-a-date")).toBe("not-a-date");
  });

  it("renders a fixed instant in IST (en-IN, 24h)", () => {
    // 2026-01-15T00:00:00Z is 05:30:00 IST on 15/01/26.
    const out = fmtTime("2026-01-15T00:00:00Z");
    expect(out).toContain("15/01/26");
    expect(out).toContain("05:30:00");
  });
});

describe("fmtDateTime", () => {
  it("returns an em-dash for empty or invalid input", () => {
    expect(fmtDateTime(null)).toBe("—");
    expect(fmtDateTime(undefined)).toBe("—");
    expect(fmtDateTime("")).toBe("—");
    expect(fmtDateTime("nope")).toBe("—");
  });

  it("renders short month + day + time (locale-dependent shape)", () => {
    const out = fmtDateTime("2026-01-15T12:00:00Z");
    // e.g. "Jan 15 05:30 PM" / "15 Jan 17:30" depending on runtime locale.
    expect(out).not.toBe("—");
    expect(out).toMatch(/\d{2}/);
  });
});

describe("fmtNumber", () => {
  it("uses 1 decimal for |value| >= 100 and 3 below", () => {
    expect(fmtNumber(123.456)).toBe("123.5");
    expect(fmtNumber(-250.04)).toBe("-250.0");
    expect(fmtNumber(99.12345)).toBe("99.123");
    expect(fmtNumber(0)).toBe("0.000");
  });

  it("stringifies non-numbers untouched", () => {
    expect(fmtNumber("abc")).toBe("abc");
    expect(fmtNumber(null)).toBe("null");
    expect(fmtNumber(undefined)).toBe("undefined");
  });
});

describe("formatTime12h", () => {
  it("renders a 12-hour clock time with seconds", () => {
    const out = formatTime12h("2026-01-15T13:05:09");
    expect(out).toMatch(/^\d{1,2}:\d{2}:\d{2}\s?(AM|PM)$/);
  });

  it("propagates invalid dates as Invalid Date", () => {
    expect(formatTime12h("not-a-date")).toBe("Invalid Date");
  });
});
