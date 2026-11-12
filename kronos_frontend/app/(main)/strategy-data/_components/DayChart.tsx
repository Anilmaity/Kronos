"use client";

import React, { useEffect, useRef, useState } from "react";
import {
  createChart,
  createSeriesMarkers,
  CandlestickSeries,
  SeriesMarker,
  Time,
  UTCTimestamp,
} from "lightweight-charts";
import { gql } from "@apollo/client";

import { client } from "@/GraphQL/client";
import { middleware } from "@/GraphQL/middleware";
import { soft } from "@/lib/tvStyles";

export interface Trade {
  entryTime: number;
  exitTime: number;
  side: string;
  entryPrice: number;
  exitPrice: number;
  stopLoss: number | null;
  takeProfit: number | null;
  pnlUsd: number;
  outcome: string;
  note: string;
}

// Operator chart style (same as /chart): green up / black down on #DBDBDB, no grid.
const UP = "#089981";
const DOWN = "#000000";

const CANDLES = gql`
  query DayCandles($before: Int) {
    candles(symbol: "XAU_USD", interval: "1m", limit: 1440, before: $before) {
      time
      open
      high
      low
      close
    }
  }
`;

// 1-minute candles for one UTC day with an arrow at every entry and exit.
const DayChart = ({ day, trades }: { day: string; trades: Trade[] }) => {
  const ref = useRef<HTMLDivElement | null>(null);
  const [state, setState] = useState<"loading" | "ok" | "empty" | "failed">("loading");

  useEffect(() => {
    if (!ref.current) return undefined;
    const dayStart = Date.parse(`${day}T00:00:00Z`) / 1000;
    const chart = createChart(ref.current, {
      autoSize: true,
      layout: { background: { color: "#DBDBDB" }, textColor: "#000000" },
      grid: { vertLines: { visible: false }, horzLines: { visible: false } },
      rightPriceScale: { borderColor: "#B8B8B8" },
      timeScale: { borderColor: "#B8B8B8", timeVisible: true },
    });
    const series = chart.addSeries(CandlestickSeries, {
      priceFormat: { type: "price", precision: 2, minMove: 0.01 },
      upColor: UP,
      downColor: DOWN,
      borderUpColor: DOWN,
      borderDownColor: DOWN,
      wickUpColor: DOWN,
      wickDownColor: DOWN,
    });
    let alive = true;
    setState("loading");
    client
      .query({ query: CANDLES, variables: { before: dayStart + 86400 }, fetchPolicy: "no-cache" })
      .then(({ data }) => {
        if (!alive) return;
        const bars = (data.candles ?? []).filter((c: { time: number }) => c.time >= dayStart);
        series.setData(bars.map((c: any) => ({ ...c, time: c.time as UTCTimestamp })));
        // Markers must sit on an existing bar: snap each to its minute.
        const snap = (t: number) => (t - (t % 60)) as UTCTimestamp;
        const markers: SeriesMarker<Time>[] = [];
        trades.forEach((t, i) => {
          const buy = t.side === "BUY";
          markers.push({
            time: snap(t.entryTime),
            position: buy ? "belowBar" : "aboveBar",
            shape: buy ? "arrowUp" : "arrowDown",
            color: buy ? "#007AFF" : "#FF3B30",
            text: `${i + 1} ${t.side}`,
          });
          markers.push({
            time: snap(Math.min(t.exitTime - 1, dayStart + 86399)),
            position: buy ? "aboveBar" : "belowBar",
            shape: "circle",
            color: t.pnlUsd >= 0 ? UP : "#FF3B30",
            text: `${i + 1} ${t.pnlUsd >= 0 ? "+" : "-"}$${Math.abs(t.pnlUsd).toFixed(2)}`,
          });
        });
        createSeriesMarkers(series, markers.sort((a, b) => Number(a.time) - Number(b.time)));
        chart.timeScale().fitContent();
        setState(bars.length ? "ok" : "empty");
      })
      .catch((err) => {
        if (!alive) return;
        setState("failed");
        middleware(err);
      });
    return () => {
      alive = false;
      chart.remove();
    };
  }, [day, trades]);

  return (
    <div className="w-full flex flex-col gap-2">
      {state !== "ok" && (
        <span className="text-sm" style={soft}>
          {state === "loading" ? "Loading candles..." : state === "empty" ? "No candles for this day." : "Failed to load candles."}
        </span>
      )}
      <div ref={ref} style={{ width: "100%", height: "420px" }} />
    </div>
  );
};

export default DayChart;
