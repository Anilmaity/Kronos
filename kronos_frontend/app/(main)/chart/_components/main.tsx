'use client';

import React, { useEffect, useRef, useState, useCallback } from "react";
import {
  createChart,
  CandlestickSeries,
  IChartApi,
  ISeriesApi,
  UTCTimestamp,
} from "lightweight-charts";
import { gql } from "@apollo/client";
import { client } from "@/GraphQL/client";
import { toast } from "sonner";
import { useTheme } from "next-themes";
import { chartTheme } from "@/utils/chartTheme";

interface CandleData {
  time: UTCTimestamp;
  open: number;
  high: number;
  low: number;
  close: number;
}

const INTERVALS = ["5s", "15s", "30s", "1m", "5m", "15m", "1h", "4h", "1d"] as const;
type Interval = (typeof INTERVALS)[number];

const SYMBOL = "XAU_USD";
const CANDLE_LIMIT = 500;
const POLL_MS = 10_000;
const STORAGE_KEY = "kronos:chart:interval";

const CANDLES_QUERY = gql`
  query Candles($symbol: String!, $interval: String!, $limit: Int) {
    candles(symbol: $symbol, interval: $interval, limit: $limit) {
      time
      open
      high
      low
      close
    }
  }
`;

const CandleChart = () => {
  const chartContainerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const legendRef = useRef<HTMLDivElement | null>(null);
  const firstLoadRef = useRef(true);

  const { resolvedTheme } = useTheme();

  const [interval, setIntervalState] = useState<Interval>(() => {
    if (typeof window === "undefined") return "5m";
    const stored = window.localStorage.getItem(STORAGE_KEY) as Interval | null;
    return stored && INTERVALS.includes(stored) ? stored : "5m";
  });

  const fetchData = useCallback(async (tf: Interval) => {
    try {
      const res = await client.query({
        query: CANDLES_QUERY,
        variables: { symbol: SYMBOL, interval: tf, limit: CANDLE_LIMIT },
        fetchPolicy: "no-cache",
      });
      const candles: CandleData[] = res.data.candles ?? [];
      candleSeriesRef.current?.setData(candles);
      if (firstLoadRef.current && candles.length > 0) {
        chartRef.current?.timeScale().fitContent();
        firstLoadRef.current = false;
      }
    } catch (err: any) {
      toast.error(err.message);
      console.error(err);
    }
  }, []);

  // One-time chart creation — dark defaults; theme effect applies correct colours immediately after
  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: chartContainerRef.current.clientHeight,
      layout: {
        background: { color: "#131722" },
        textColor: "#787B86",
      },
      grid: {
        vertLines: { color: "#2A2E39" },
        horzLines: { color: "#2A2E39" },
      },
      timeScale: { borderColor: "#2A2E39", timeVisible: true, secondsVisible: true },
    });
    chart.applyOptions({
      rightPriceScale: { scaleMargins: { top: 0.1, bottom: 0.1 } },
      crosshair: { horzLine: { visible: false, labelVisible: false } },
    });
    chartRef.current = chart;

    candleSeriesRef.current = chart.addSeries(CandlestickSeries, {
      priceFormat: { type: "price", precision: 2, minMove: 0.01 },
      upColor: "#089981",
      downColor: "#F23645",
      borderVisible: false,
      wickUpColor: "#089981",
      wickDownColor: "#F23645",
    });

    // Legend overlay — uses CSS custom properties so it tracks theme changes automatically
    const legend = document.createElement("div");
    legend.style.position = "absolute";
    legend.style.left = "12px";
    legend.style.top = "12px";
    legend.style.zIndex = "1";
    legend.style.fontSize = "12px";
    legend.style.fontWeight = "500";
    legend.style.lineHeight = "20px";
    legend.style.color = "var(--tv-text-1)";
    legend.style.backgroundColor = "var(--tv-surface)";
    legend.style.padding = "8px 10px";
    legend.style.borderRadius = "6px";
    legend.style.border = "1px solid var(--tv-border)";
    legend.style.pointerEvents = "none";
    chartContainerRef.current.appendChild(legend);
    legendRef.current = legend;

    chart.subscribeCrosshairMove((param) => {
      const candleData = param.seriesData.get(candleSeriesRef.current!);
      if (!candleData) {
        legend.innerHTML = "";
        return;
      }
      const { open, high, low, close } = candleData as CandleData;
      const isGreen = close >= open;
      // Use CSS custom properties so legend OHLC colours follow the theme without JS
      const color = isGreen ? "var(--tv-up)" : "var(--tv-down)";
      legend.innerHTML = `
        <div style="font-weight:600;color:var(--tv-text-1);">${SYMBOL}</div>
        <div>
          O: <span style="color:${color};">${open.toFixed(2)}</span>
          H: <span style="color:${color};">${high.toFixed(2)}</span>
          L: <span style="color:${color};">${low.toFixed(2)}</span>
          C: <span style="color:${color};">${close.toFixed(2)}</span>
        </div>
      `;
    });

    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        chart.applyOptions({ width: entry.contentRect.width, height: entry.contentRect.height });
      }
    });
    resizeObserver.observe(chartContainerRef.current);

    return () => {
      resizeObserver.disconnect();
      chart.remove();
      chartRef.current = null;
      candleSeriesRef.current = null;
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Re-apply chart colours whenever the resolved theme changes
  useEffect(() => {
    if (!chartRef.current || !candleSeriesRef.current) return;
    const t = chartTheme(resolvedTheme === "light" ? "light" : "dark");

    chartRef.current.applyOptions({
      layout: { background: { color: t.bg }, textColor: t.text3 },
      grid: { vertLines: { color: t.border }, horzLines: { color: t.border } },
      timeScale: { borderColor: t.border },
    });

    candleSeriesRef.current.applyOptions({
      upColor: t.up,
      downColor: t.down,
      borderVisible: false,
      wickUpColor: t.up,
      wickDownColor: t.down,
    });
  }, [resolvedTheme]);

  // Refetch + polling whenever interval changes
  useEffect(() => {
    if (!candleSeriesRef.current) return;
    firstLoadRef.current = true;
    candleSeriesRef.current.setData([]);
    fetchData(interval);
    const id = window.setInterval(() => fetchData(interval), POLL_MS);
    return () => window.clearInterval(id);
  }, [interval, fetchData]);

  const onSelectInterval = (tf: Interval) => {
    setIntervalState(tf);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(STORAGE_KEY, tf);
    }
  };

  return (
    <div className="w-full">
      {/* Toolbar — Task 5.1 style mapping applied */}
      <div className="flex items-center gap-2 mb-2">
        <span
          className="mr-2"
          style={{
            fontSize: 11,
            fontWeight: 500,
            textTransform: "uppercase",
            letterSpacing: "0.4px",
            color: "var(--tv-text-3)",
          }}
        >
          Interval:
        </span>
        {INTERVALS.map((tf) => {
          const active = tf === interval;
          return (
            <button
              key={tf}
              type="button"
              onClick={() => onSelectInterval(tf)}
              className={
                active
                  ? "px-3 py-1 text-sm transition-colors bg-[var(--tv-accent)] hover:bg-[var(--tv-accent-hover)]"
                  : "px-3 py-1 text-sm transition-colors bg-[var(--tv-surface)] hover:bg-[var(--tv-surface-2)]"
              }
              style={
                active
                  ? {
                      color: "#fff",
                      borderRadius: "6px",
                    }
                  : {
                      color: "var(--tv-text-2)",
                      borderRadius: "6px",
                      border: "1px solid var(--tv-border)",
                    }
              }
            >
              {tf}
            </button>
          );
        })}
      </div>
      <div className="relative w-full h-[80vh]">
        <div ref={chartContainerRef} className="w-full h-full" />
      </div>
    </div>
  );
};

export default CandleChart;
