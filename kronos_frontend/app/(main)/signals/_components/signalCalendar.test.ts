import { describe, expect, it } from "vitest";

import {
  buildWeeks,
  bucketByDay,
  dayLabel,
  istDayKey,
  monthSummary,
  monthWindowUtc,
  CalendarSignal,
} from "./signalCalendar";

describe("istDayKey", () => {
  it("maps a UTC instant to its IST calendar day", () => {
    // 18:30:00Z is exactly 00:00 IST the NEXT day
    expect(istDayKey("2026-07-31T18:30:00.000Z")).toBe("2026-08-01");
  });
  it("keeps instants just before the IST midnight on the same IST day", () => {
    expect(istDayKey("2026-07-31T18:29:59.999Z")).toBe("2026-07-31");
  });
  it("returns null for null and unparseable input", () => {
    expect(istDayKey(null)).toBeNull();
    expect(istDayKey("not-a-date")).toBeNull();
  });
});

describe("monthWindowUtc", () => {
  it("covers the IST month for August 2026", () => {
    expect(monthWindowUtc(2026, 8)).toEqual({
      since: "2026-07-31T18:30:00.000Z",
      until: "2026-08-31T18:29:59.999Z",
    });
  });
  it("crosses the year boundary for January", () => {
    expect(monthWindowUtc(2026, 1)).toEqual({
      since: "2025-12-31T18:30:00.000Z",
      until: "2026-01-31T18:29:59.999Z",
    });
  });
});

const sig = (signalAt: string | null, status: string): CalendarSignal => ({
  signalAt,
  status,
});

describe("bucketByDay", () => {
  const signals: CalendarSignal[] = [
    sig("2026-08-01T04:00:00.000Z", "PLACED"),   // Aug 1 IST
    sig("2026-08-01T05:00:00.000Z", "REJECTED"), // Aug 1 IST
    sig("2026-08-01T06:00:00.000Z", "REJECTED"), // Aug 1 IST
    sig("2026-08-01T18:30:00.000Z", "FIRED"),    // Aug 2 IST (rolls over)
    sig(null, "PLACED"),                          // no timestamp - excluded
    sig("2026-08-01T07:00:00.000Z", "WEIRD"),    // unknown status - no chip
  ];

  it("splits counts by status per IST day", () => {
    expect(bucketByDay(signals, "ALL")).toEqual({
      "2026-08-01": { placed: 1, rejected: 2, fired: 0 },
      "2026-08-02": { placed: 0, rejected: 0, fired: 1 },
    });
  });

  it("applies the status filter", () => {
    expect(bucketByDay(signals, "REJECTED")).toEqual({
      "2026-08-01": { placed: 0, rejected: 2, fired: 0 },
    });
  });
});

describe("monthSummary", () => {
  it("counts every row in total, known statuses in their buckets", () => {
    const signals: CalendarSignal[] = [
      sig("2026-08-01T04:00:00.000Z", "PLACED"),
      sig("2026-08-01T05:00:00.000Z", "REJECTED"),
      sig(null, "FIRED"),
      sig("2026-08-01T07:00:00.000Z", "WEIRD"),
    ];
    expect(monthSummary(signals)).toEqual({
      total: 4,
      placed: 1,
      rejected: 1,
      fired: 1,
    });
  });
});

describe("buildWeeks", () => {
  it("builds Monday-start weeks covering August 2026", () => {
    const weeks = buildWeeks(2026, 8);
    expect(weeks).toHaveLength(6);
    expect(weeks.every((w) => w.length === 7)).toBe(true);
    // Aug 1 2026 is a Saturday -> 5 leading July cells
    expect(weeks[0][0]).toEqual({
      key: "2026-07-27",
      dayNumber: 27,
      inMonth: false,
    });
    expect(weeks[0][5]).toEqual({
      key: "2026-08-01",
      dayNumber: 1,
      inMonth: true,
    });
    expect(weeks[5][6].key).toBe("2026-09-06");
  });
});

describe("dayLabel", () => {
  it("renders a short weekday-day-month label", () => {
    expect(dayLabel("2026-08-01")).toBe("Sat 01 Aug");
  });
});
