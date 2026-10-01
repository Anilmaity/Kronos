"use client";
import React, { useState } from "react";

import StrategyTable from "./StrategyTable";
import DatePicker from "@/app/(main)/dashboard/_components/DatePicker";
import { StrategySource } from "./strategySources";

const DashboardPage = ({
  label = "01 — Dashboard",
  source,
}: {
  label?: string;
  source?: StrategySource;
}) => {
  const [brokerIds] = useState<string[]>([]);
  const [isLoading] = useState(false);

  const [selectedDate, setSelectedDate] = useState<Date>(new Date());

  const creationDate = new Date("2024-01-01");

  const handleDatePickerChange = (date: Date) => {
    setSelectedDate(date);
  };

  if (isLoading) {
    return (
      <div
        style={{
          fontSize: "11px",
          fontWeight: 500,
          letterSpacing: "0.4px",
          textTransform: "uppercase",
          color: "var(--tv-text-3)",
          padding: "40px",
        }}
      >
        ◆ Loading…
      </div>
    );
  }

  return (
    <div className="flex flex-col items-start w-full gap-6">

      {/* ── Top bar: section label + date picker ── */}
      <div className="flex items-center justify-between w-full gap-4 flex-wrap">
        {/* Section label */}
        <div className="flex items-center gap-3">
          <span
            style={{
              fontSize: "11px",
              fontWeight: 500,
              letterSpacing: "0.4px",
              textTransform: "uppercase",
              color: "var(--tv-text-3)",
            }}
          >
            {label}
          </span>
        </div>

        {/* Date picker — right aligned */}
        <div className="flex items-center gap-3">
          <span
            style={{
              fontSize: "11px",
              fontWeight: 500,
              letterSpacing: "0.4px",
              textTransform: "uppercase",
              color: "var(--tv-text-3)",
            }}
          >
            Date
          </span>
          <DatePicker
            selectedDate={selectedDate}
            createdAtDate={creationDate}
            onSelectDate={handleDatePickerChange}
          />
        </div>
      </div>

      {/* ── Positions ── */}
      <div className="w-full">
        <StrategyTable selectedDate={selectedDate} brokerIds={brokerIds} source={source} />
      </div>
    </div>
  );
};

export default DashboardPage;
