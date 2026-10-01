"use client";
// History of a copy-trade tab (Neymar / Neymar VIP): every signal the channel
// posted, day by day, with the orders each account placed and how they ended.
import React, { useEffect, useMemo, useState } from "react";
import { gql } from "@apollo/client";

import { client } from "@/GraphQL/client";
import { middleware } from "@/GraphQL/middleware";

import { StrategySource } from "./strategySources";

const GET_HISTORY = gql`
  query CopyTradeHistory($source: String!, $days: Int) {
    copyTradeHistory(source: $source, days: $days) {
      msgId
      postedAt
      side
      entryLow
      entryHigh
      sl
      tps
      totalVolume
      status
      closeReason
      realizedPnl
      closedAt
      raw
      traded
      rejectionReason
      orders {
        account
        tpIndex
        kind
        volume
        entry
        fillPrice
        sl
        tp
        brokerState
        realizedPnl
        createdAt
        closedAt
        ticketId
      }
    }
  }
`;

interface HistoryOrder {
  account: string;
  tpIndex: number;
  kind: string;
  volume: number | null;
  entry: number | null;
  fillPrice: number | null;
  sl: number | null;
  tp: number | null;
  brokerState: string | null;
  realizedPnl: number | null;
  createdAt: string | null;
  closedAt: string | null;
  ticketId: string;
}

interface HistorySignal {
  msgId: string | null;
  postedAt: string | null;
  side: string;
  entryLow: number | null;
  entryHigh: number | null;
  sl: number | null;
  tps: number[];
  totalVolume: number | null;
  status: string | null;
  closeReason: string | null;
  realizedPnl: number | null;
  closedAt: string | null;
  raw: string | null;
  traded: boolean;
  rejectionReason: string | null;
  orders: HistoryOrder[];
}

const IST = "Asia/Kolkata";
const dayKey = (iso: string) =>
  new Date(iso).toLocaleDateString("en-CA", { timeZone: IST }); // YYYY-MM-DD
const dayLabel = (key: string) =>
  new Date(`${key}T12:00:00+05:30`).toLocaleDateString("en-IN", {
    timeZone: IST,
    weekday: "short",
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
const time = (iso: string | null) =>
  iso ? new Date(iso).toLocaleTimeString("en-IN", { timeZone: IST, hour: "2-digit", minute: "2-digit" }) : "—";
const px = (v: number | null | undefined) => (v === null || v === undefined ? "—" : v.toFixed(2));

const pnl = (v: number | null | undefined) => {
  if (v === null || v === undefined) return <span style={{ color: "var(--tv-text-3)" }}>—</span>;
  return (
    <span className="tnum" style={{ color: v < 0 ? "var(--tv-down)" : "var(--tv-up)", fontWeight: 600 }}>
      {v > 0 ? "+" : ""}
      {v.toFixed(2)}
    </span>
  );
};

const RESULT: Record<string, string> = {
  broker_tp: "TP hit",
  broker_sl: "SL hit",
  broker_cancelled: "Not filled",
  tp3: "All TPs (channel)",
  sl: "SL (channel)",
  channel_close: "Closed by channel",
  expired: "Expired (12h)",
  superseded: "Replaced by next signal",
  breakeven_exit: "Breakeven exit",
};

const signalResult = (s: HistorySignal) => {
  if (!s.traded) return { text: "Not traded", color: "var(--tv-text-3)" };
  const reason = s.closeReason || (s.status?.startsWith("closed_") ? s.status.slice(7) : null);
  if (!reason) return { text: "Open", color: "var(--tv-accent)" };
  return { text: RESULT[reason] ?? reason, color: "var(--tv-text-2)" };
};

const ORDER_STATE: Record<string, string> = {
  filled: "Open",
  pending: "Pending",
  closed: "Closed",
  cancelled: "Cancelled (not filled)",
};

const cell: React.CSSProperties = { padding: "6px 8px", whiteSpace: "nowrap" };
const head: React.CSSProperties = {
  ...cell,
  fontSize: "11px",
  fontWeight: 500,
  letterSpacing: "0.4px",
  textTransform: "uppercase",
  color: "var(--tv-text-3)",
  textAlign: "left",
};

const SignalBlock = ({ s }: { s: HistorySignal }) => {
  const [showMsg, setShowMsg] = useState(false);
  const res = signalResult(s);
  const accounts = Array.from(new Set(s.orders.map((o) => o.account)));
  return (
    <div style={{ borderTop: "1px solid var(--tv-border)" }}>
      {/* Signal */}
      <div className="flex flex-wrap items-center gap-x-6 gap-y-1 px-3 py-3" style={{ fontSize: "13px" }}>
        <span className="tnum font-semibold">{time(s.postedAt)}</span>
        <span
          style={{
            fontWeight: 700,
            color: s.side === "buy" ? "var(--tv-up)" : "var(--tv-down)",
            textTransform: "uppercase",
          }}
        >
          {s.side}
        </span>
        <span className="tnum">
          Entry {s.entryLow === s.entryHigh ? px(s.entryLow) : `${px(s.entryLow)} – ${px(s.entryHigh)}`}
        </span>
        <span className="tnum">SL {px(s.sl)}</span>
        <span className="tnum">TP {s.tps.length ? s.tps.map((t) => t.toFixed(2)).join(" · ") : "—"}</span>
        {s.totalVolume !== null && <span className="tnum">Lot {s.totalVolume.toFixed(2)}</span>}
        <span style={{ color: res.color, fontWeight: 600 }}>{res.text}</span>
        <span>P&amp;L {pnl(s.realizedPnl)}</span>
        {s.msgId && <span style={{ color: "var(--tv-text-3)", fontSize: "11px" }}>msg {s.msgId}</span>}
        {s.raw && (
          <button onClick={() => setShowMsg(!showMsg)} style={{ color: "var(--tv-accent)", fontSize: "12px" }}>
            {showMsg ? "Hide message" : "Message"}
          </button>
        )}
      </div>
      {!s.traded && s.rejectionReason && (
        <div className="px-3 pb-3" style={{ fontSize: "12px", color: "var(--tv-text-3)" }}>
          Why not traded: {s.rejectionReason}
        </div>
      )}
      {showMsg && s.raw && (
        <pre
          className="mx-3 mb-3 p-3"
          style={{
            whiteSpace: "pre-wrap",
            fontSize: "12px",
            background: "var(--tv-surface-2)",
            borderRadius: "6px",
            color: "var(--tv-text-2)",
          }}
        >
          {s.raw}
        </pre>
      )}

      {/* Orders placed for this signal, per account */}
      {accounts.map((acct) => {
        const orders = s.orders.filter((o) => o.account === acct);
        const total = orders.reduce((n, o) => n + (o.realizedPnl ?? 0), 0);
        const hasPnl = orders.some((o) => o.realizedPnl !== null);
        return (
          <div key={acct} className="mx-3 mb-3 overflow-x-auto" style={{ border: "1px solid var(--tv-border)", borderRadius: "6px" }}>
            <div className="flex items-center justify-between px-3 py-2" style={{ background: "var(--tv-surface-2)", fontSize: "12px" }}>
              <span className="font-semibold">{acct}</span>
              <span>
                {orders.length} order{orders.length === 1 ? "" : "s"} · P&amp;L {hasPnl ? pnl(total) : pnl(null)}
              </span>
            </div>
            <table className="w-full" style={{ fontSize: "12px" }}>
              <thead>
                <tr>
                  <th style={head}>Trade</th>
                  <th style={head}>Type</th>
                  <th style={head}>Lot</th>
                  <th style={head}>Entry</th>
                  <th style={head}>SL</th>
                  <th style={head}>TP</th>
                  <th style={head}>Status</th>
                  <th style={head}>Opened</th>
                  <th style={head}>Closed</th>
                  <th style={{ ...head, textAlign: "right" }}>P&amp;L</th>
                </tr>
              </thead>
              <tbody>
                {orders.map((o) => (
                  <tr key={o.ticketId} style={{ borderTop: "1px solid var(--tv-border)" }}>
                    <td style={cell} className="tnum">
                      {o.tpIndex > 100
                        ? `TP${o.tpIndex % 100} re-entry ${Math.floor(o.tpIndex / 100)}`
                        : `TP${o.tpIndex}`}
                    </td>
                    <td style={cell}>{o.kind}</td>
                    <td style={cell} className="tnum">{o.volume?.toFixed(2) ?? "—"}</td>
                    <td style={cell} className="tnum">{px(o.fillPrice ?? o.entry)}</td>
                    <td style={cell} className="tnum">{px(o.sl)}</td>
                    <td style={cell} className="tnum">{o.tp === null ? "open" : px(o.tp)}</td>
                    <td style={cell}>{ORDER_STATE[o.brokerState ?? ""] ?? o.brokerState ?? "—"}</td>
                    <td style={cell} className="tnum">{time(o.createdAt)}</td>
                    <td style={cell} className="tnum">{time(o.closedAt)}</td>
                    <td style={{ ...cell, textAlign: "right" }}>{pnl(o.realizedPnl)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
      })}
      {s.traded && accounts.length === 0 && (
        <div className="px-3 pb-3" style={{ fontSize: "12px", color: "var(--tv-text-3)" }}>
          No orders on your accounts for this signal.
        </div>
      )}
    </div>
  );
};

const CopyTradeHistory = ({ source }: { source: StrategySource }) => {
  const [days, setDays] = useState(30);
  const [rows, setRows] = useState<HistorySignal[] | null>(null);

  useEffect(() => {
    let stop = false;
    const load = () =>
      client
        .query({ query: GET_HISTORY, variables: { source, days }, fetchPolicy: "no-cache" })
        .then(({ data }) => !stop && setRows(data.copyTradeHistory ?? []))
        .catch((err) => middleware(err));
    setRows(null);
    load();
    const id = setInterval(load, 30000);
    return () => {
      stop = true;
      clearInterval(id);
    };
  }, [source, days]);

  const byDay = useMemo(() => {
    const m = new Map<string, HistorySignal[]>();
    for (const r of rows ?? []) {
      if (!r.postedAt) continue;
      const k = dayKey(r.postedAt);
      m.set(k, [...(m.get(k) ?? []), r]);
    }
    return Array.from(m.entries());
  }, [rows]);

  const totals = useMemo(() => {
    const traded = (rows ?? []).filter((r) => r.traded);
    const closed = traded.filter((r) => r.realizedPnl !== null);
    return {
      signals: rows?.length ?? 0,
      traded: traded.length,
      wins: closed.filter((r) => (r.realizedPnl ?? 0) > 0).length,
      losses: closed.filter((r) => (r.realizedPnl ?? 0) < 0).length,
      pnl: closed.reduce((n, r) => n + (r.realizedPnl ?? 0), 0),
    };
  }, [rows]);

  return (
    <div className="w-full flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap gap-4" style={{ fontSize: "13px" }}>
          <span>Signals <b>{totals.signals}</b></span>
          <span>Traded <b>{totals.traded}</b></span>
          <span>
            Profit <b style={{ color: "var(--tv-up)" }}>{totals.wins}</b> · Loss{" "}
            <b style={{ color: "var(--tv-down)" }}>{totals.losses}</b>
          </span>
          <span>P&amp;L {pnl(rows ? totals.pnl : null)}</span>
        </div>
        <div className="flex gap-1">
          {[7, 30, 90, 365].map((d) => (
            <button
              key={d}
              onClick={() => setDays(d)}
              style={{
                padding: "4px 10px",
                borderRadius: "6px",
                fontSize: "12px",
                border: "1px solid var(--tv-border)",
                background: d === days ? "var(--tv-accent)" : "transparent",
                color: d === days ? "#fff" : "var(--tv-text-2)",
              }}
            >
              {d === 365 ? "1 year" : `${d} days`}
            </button>
          ))}
        </div>
      </div>

      {rows === null && <div style={{ color: "var(--tv-text-3)", fontSize: "13px" }}>Loading history…</div>}
      {rows !== null && byDay.length === 0 && (
        <div
          className="flex items-center justify-center py-16"
          style={{ background: "var(--tv-surface)", border: "1px solid var(--tv-border)", borderRadius: "6px", color: "var(--tv-text-3)" }}
        >
          No signals in this period
        </div>
      )}
      {byDay.map(([day, signals]) => {
        const dayPnl = signals.reduce((n, s) => n + (s.realizedPnl ?? 0), 0);
        const anyPnl = signals.some((s) => s.realizedPnl !== null);
        return (
          <div key={day} style={{ background: "var(--tv-surface)", border: "1px solid var(--tv-border)", borderRadius: "6px" }}>
            <div className="flex items-center justify-between px-3 py-2" style={{ fontSize: "12px" }}>
              <span className="font-semibold" style={{ fontSize: "13px" }}>{dayLabel(day)}</span>
              <span>
                {signals.length} signal{signals.length === 1 ? "" : "s"} · {signals.filter((s) => s.traded).length} traded · P&amp;L{" "}
                {anyPnl ? pnl(dayPnl) : pnl(null)}
              </span>
            </div>
            {signals.map((s, i) => (
              <SignalBlock key={`${s.msgId ?? "x"}-${s.postedAt}-${i}`} s={s} />
            ))}
          </div>
        );
      })}
    </div>
  );
};

export default CopyTradeHistory;
