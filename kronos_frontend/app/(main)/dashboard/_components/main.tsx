"use client";
import React, { useState } from "react";

import StrategyTable from "./StrategyTable";
import DatePicker from "@/app/(main)/dashboard/_components/DatePicker";
import { StrategySource } from "./strategySources";
import { AddCopyTradeDialog } from "./CopyTradeDialogs";
import CopyTradeHistory from "./CopyTradeHistory";
import { useStrategyChangeHappend } from "@/hooks/useStrategyChangeHappend";

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
  const [addOpen, setAddOpen] = useState(false);
  const [view, setView] = useState<"accounts" | "history">("accounts");
  const [rowCount, setRowCount] = useState(0);
  const { setStrategyChangeHappend } = useStrategyChangeHappend();

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

  const viewTab = (key: "accounts" | "history", label: string) => (
    <button
      onClick={() => setView(key)}
      style={{
        padding: "6px 16px",
        fontSize: "13px",
        fontWeight: 600,
        borderBottom: `2px solid ${view === key ? "var(--tv-accent)" : "transparent"}`,
        color: view === key ? "var(--tv-text)" : "var(--tv-text-3)",
      }}
    >
      {label}
    </button>
  );

  return (
    <div className="flex flex-col items-start w-full gap-6">
      {/* Copy-trade tabs: Accounts (live) | History (every signal + your orders) */}
      {source && (
        <div className="flex items-center gap-2 w-full" style={{ borderBottom: "1px solid var(--tv-border)" }}>
          {viewTab("accounts", "Accounts")}
          {viewTab("history", "History")}
        </div>
      )}

      {source && view === "history" ? (
        <CopyTradeHistory source={source} />
      ) : (
      <>

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

        {/* Date picker — right aligned (copy-trade tabs: Add Data first) */}
        <div className="flex items-center gap-3">
          {source && (
            <button
              onClick={() => setAddOpen(true)}
              style={{
                height: "32px",
                padding: "0 14px",
                borderRadius: "6px",
                fontSize: "12px",
                fontWeight: 600,
                background: "var(--tv-accent)",
                color: "#fff",
              }}
            >
              + Add Data
            </button>
          )}
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
        <StrategyTable
          selectedDate={selectedDate}
          brokerIds={brokerIds}
          source={source}
          onRowCount={setRowCount}
        />
      </div>
      </>
      )}
      {source && (
        <AddCopyTradeDialog
          open={addOpen}
          onOpenChange={setAddOpen}
          source={source}
          nextNumber={rowCount + 1}
          onAdded={() => setStrategyChangeHappend(true)}
        />
      )}
    </div>
  );
};

export default DashboardPage;
