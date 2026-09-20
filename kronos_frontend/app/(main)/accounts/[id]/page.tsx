/* eslint-disable react-hooks/exhaustive-deps */
"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";

import { client } from "@/GraphQL/client";
import { isAuthFailure, middleware } from "@/GraphQL/middleware";
import { GET_ACCOUNT_ANALYTICS, AccountAnalytics } from "@/GraphQL/accountControls";
import EquityChart from "../../manager-backtest/_components/EquityChart";
import { panelStyle, soft } from "@/lib/tvStyles";
import { pnlColor } from "@/utils/format";

type Preset = "all" | "30d" | "90d" | "ytd" | "custom";

const PRESETS: { key: Preset; label: string }[] = [
  { key: "all", label: "All-time" },
  { key: "30d", label: "30d" },
  { key: "90d", label: "90d" },
  { key: "ytd", label: "YTD" },
  { key: "custom", label: "Custom" },
];

const toIsoDate = (d: Date): string => d.toISOString().slice(0, 10);

// Resolves a preset (plus the custom-range inputs) to concrete fromDate/toDate
// ISO strings. "All-time" (and an unfilled "Custom") omit both, which the
// backend treats as no lower/upper bound.
const presetRange = (
  preset: Preset,
  customFrom: string,
  customTo: string
): { fromDate?: string; toDate?: string } => {
  const today = new Date();
  switch (preset) {
    case "30d": {
      const from = new Date(today);
      from.setDate(from.getDate() - 30);
      return { fromDate: toIsoDate(from), toDate: toIsoDate(today) };
    }
    case "90d": {
      const from = new Date(today);
      from.setDate(from.getDate() - 90);
      return { fromDate: toIsoDate(from), toDate: toIsoDate(today) };
    }
    case "ytd": {
      const from = new Date(today.getFullYear(), 0, 1);
      return { fromDate: toIsoDate(from), toDate: toIsoDate(today) };
    }
    case "custom":
      return { fromDate: customFrom || undefined, toDate: customTo || undefined };
    case "all":
    default:
      return {};
  }
};

const chipStyle = (selected: boolean): React.CSSProperties => ({
  fontSize: "12px",
  fontWeight: 600,
  borderRadius: "4px",
  padding: "5px 12px",
  border: `1px solid ${selected ? "var(--tv-accent)" : "var(--tv-border)"}`,
  color: selected ? "var(--tv-accent)" : "var(--tv-text-soft)",
  cursor: "pointer",
  background: selected
    ? "color-mix(in srgb, var(--tv-accent) 8%, transparent)"
    : "transparent",
});

const dateFieldStyle: React.CSSProperties = {
  background: "var(--tv-bg)",
  border: "1px solid var(--tv-border)",
  borderRadius: "6px",
  padding: "5px 8px",
  fontSize: "12px",
  color: "inherit",
};

const fmtUsd = (n: number | null | undefined): string =>
  n === null || n === undefined ? "—" : `$${n.toFixed(2)}`;

const fmtPct = (n: number | null | undefined): string =>
  n === null || n === undefined ? "—" : `${n.toFixed(1)}%`;

const fmtNum = (n: number | null | undefined, digits = 2): string =>
  n === null || n === undefined ? "—" : n.toFixed(digits);

const KpiTile = ({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color?: string;
}) => (
  <div
    className="flex flex-col gap-1 px-4 py-3 min-w-[150px]"
    style={panelStyle}
  >
    <span className="text-xs uppercase tracking-wide" style={soft}>
      {label}
    </span>
    <span className="text-lg font-semibold tnum" style={color ? { color } : undefined}>
      {value}
    </span>
  </div>
);

// Stamps a fetched payload with the request args it actually answers, so a
// late-resolving fetch from a previous account id / date range can never be
// rendered over the current selection (same pattern as reports/_components/main.tsx).
interface FetchResult {
  data: AccountAnalytics | null;
  forId: string;
  forFromDate?: string;
  forToDate?: string;
}

const AccountAnalyticsPage = () => {
  const params = useParams<{ id: string }>();
  const id = Array.isArray(params?.id) ? params.id[0] : (params?.id as string) ?? "";

  const [preset, setPreset] = useState<Preset>("all");
  const [customFrom, setCustomFrom] = useState("");
  const [customTo, setCustomTo] = useState("");

  const [result, setResult] = useState<FetchResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const requestIdRef = useRef(0);

  const { fromDate, toDate } = presetRange(preset, customFrom, customTo);

  const fetchAnalytics = useCallback(async () => {
    if (!id) return;
    const requestId = (requestIdRef.current += 1);
    const reqFromDate = fromDate;
    const reqToDate = toDate;
    setLoading(true);
    try {
      const { data } = await client.query({
        query: GET_ACCOUNT_ANALYTICS,
        variables: {
          userBrokerId: id,
          fromDate: reqFromDate ?? null,
          toDate: reqToDate ?? null,
        },
        fetchPolicy: "no-cache",
      });
      if (requestIdRef.current !== requestId) return; // superseded - drop it
      setErrorMsg(null);
      setResult({
        data: data?.accountAnalytics ?? null,
        forId: id,
        forFromDate: reqFromDate,
        forToDate: reqToDate,
      });
      setLoading(false);
    } catch (err: any) {
      if (requestIdRef.current !== requestId) return; // superseded - drop it
      if (isAuthFailure(err)) {
        middleware(err); // redirects to /login
        return;
      }
      // The backend intentionally returns the same "account not found"
      // message whether the id doesn't exist or just isn't owned by the
      // caller (it never leaks existence), so that's the message we surface.
      const raw: string = err?.graphQLErrors?.[0]?.message ?? err?.message ?? "";
      setErrorMsg(
        /fromDate must be/i.test(raw)
          ? "From date must be on or before the to date."
          : "This account was not found, or you don't have access to it."
      );
      setResult(null);
      setLoading(false);
    }
  }, [id, fromDate, toDate]);

  useEffect(() => {
    fetchAnalytics();
  }, [id, fromDate, toDate]);

  const stampMatchesCurrent =
    result !== null &&
    result.forId === id &&
    result.forFromDate === fromDate &&
    result.forToDate === toDate;

  const data = stampMatchesCurrent ? result!.data : null;
  const showLoading = loading && data === null && !errorMsg;
  const isEmpty =
    data !== null && data.kpis.trades === 0 && data.equityCurve.length === 0;

  return (
    <div className="flex flex-col items-start w-full gap-6">
      <div className="flex flex-col gap-1 w-full">
        <Link href="/accounts" className="text-xs w-fit" style={soft}>
          ← Back to accounts
        </Link>
        <div className="flex items-center gap-3 flex-wrap">
          <span className="text-base font-semibold">
            {data ? data.label || "(no label)" : "Account analytics"}
          </span>
          {data && (
            <span
              className="tv-chip"
              style={{
                cursor: "default",
                borderColor: data.isActive ? "var(--tv-up)" : "var(--tv-down)",
                color: data.isActive ? "var(--tv-up)" : "var(--tv-down)",
              }}
            >
              {data.isActive ? "active" : "archived"}
            </span>
          )}
        </div>
        {data && (
          <span className="text-sm" style={soft}>
            {data.metaAccountId}
          </span>
        )}
      </div>

      <div className="flex items-center gap-2 flex-wrap">
        {PRESETS.map((p) => (
          <button
            key={p.key}
            type="button"
            onClick={() => setPreset(p.key)}
            style={chipStyle(preset === p.key)}
          >
            {p.label}
          </button>
        ))}
        {preset === "custom" && (
          <div className="flex items-center gap-2">
            <input
              type="date"
              style={dateFieldStyle}
              value={customFrom}
              onChange={(e) => setCustomFrom(e.target.value)}
            />
            <span style={soft}>→</span>
            <input
              type="date"
              style={dateFieldStyle}
              value={customTo}
              onChange={(e) => setCustomTo(e.target.value)}
            />
          </div>
        )}
      </div>

      {showLoading && (
        <div
          className="w-full px-4 py-6 flex items-center justify-center"
          style={panelStyle}
        >
          <span className="text-sm" style={soft}>
            Loading account analytics...
          </span>
        </div>
      )}

      {errorMsg && !showLoading && (
        <div
          className="w-full px-4 py-4"
          style={{ ...panelStyle, color: "var(--tv-down)" }}
        >
          {errorMsg}
        </div>
      )}

      {data && !errorMsg && (
        <div
          className="flex flex-col gap-4 w-full"
          style={{ opacity: loading ? 0.6 : 1, transition: "opacity 150ms ease" }}
        >
          {isEmpty ? (
            <div className="w-full px-4 py-6 flex items-center justify-center" style={panelStyle}>
              <span className="text-sm" style={soft}>
                No trades in range.
              </span>
            </div>
          ) : (
            <>
              <div className="w-full overflow-x-auto">
                <div className="flex items-stretch gap-3 w-fit">
                  <KpiTile
                    label="Net P&L"
                    value={fmtUsd(data.kpis.netPnlUsd)}
                    color={pnlColor(data.kpis.netPnlUsd)}
                  />
                  <KpiTile label="Trades" value={String(data.kpis.trades)} />
                  <KpiTile label="Win Rate" value={fmtPct(data.kpis.winRate)} />
                  <KpiTile
                    label="Profit Factor"
                    value={
                      data.kpis.profitFactor === null
                        ? "—"
                        : fmtNum(data.kpis.profitFactor)
                    }
                  />
                  <KpiTile
                    label="Avg Win"
                    value={fmtUsd(data.kpis.avgWinUsd)}
                    color="var(--tv-up)"
                  />
                  <KpiTile
                    label="Avg Loss"
                    value={fmtUsd(data.kpis.avgLossUsd)}
                    color="var(--tv-down)"
                  />
                  <KpiTile
                    label="Expectancy"
                    value={fmtUsd(data.kpis.expectancyUsd)}
                    color={pnlColor(data.kpis.expectancyUsd)}
                  />
                  <KpiTile
                    label="Max Drawdown"
                    value={fmtUsd(data.kpis.maxDrawdownUsd)}
                    color="var(--tv-down)"
                  />
                  <KpiTile
                    label="Best Day"
                    value={fmtUsd(data.kpis.bestDayUsd)}
                    color="var(--tv-up)"
                  />
                  <KpiTile
                    label="Worst Day"
                    value={fmtUsd(data.kpis.worstDayUsd)}
                    color="var(--tv-down)"
                  />
                  <KpiTile
                    label="Avg Trades/Day"
                    value={fmtNum(data.kpis.avgTradesPerDay)}
                  />
                  <KpiTile
                    label="Current Balance"
                    value={fmtUsd(data.kpis.currentBalanceUsd)}
                  />
                </div>
              </div>

              <div className="w-full px-4 py-4" style={panelStyle}>
                <EquityChart
                  gated={data.equityCurve.map(
                    (p) => [p.t, p.equityUsd] as [string, number]
                  )}
                />
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
};

export default AccountAnalyticsPage;
