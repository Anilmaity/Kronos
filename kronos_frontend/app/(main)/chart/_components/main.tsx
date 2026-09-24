'use client';

import React, { useEffect, useRef, useState, useCallback } from "react";
import {
  createChart,
  createSeriesMarkers,
  CandlestickSeries,
  LineSeries,
  IChartApi,
  ISeriesApi,
  ISeriesMarkersPluginApi,
  SeriesMarker,
  Time,
  UTCTimestamp,
} from "lightweight-charts";
import { gql } from "@apollo/client";
import { client } from "@/GraphQL/client";
import { toast } from "sonner";

import { zigzag, swingLabels, hhLlPath, type SwingLabel } from "@/utils/zigzag";

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

// Market structure overlay (utils/zigzag.ts): zigzag reversal %, H/L-HH/LH-HL/LL labels,
// and the HH -> LL -> HH -> LL trend line. Off by default so the chart opens plain.
const ZIGZAG_OPTIONS = ["Off", "0.5%", "1.5%", "3%", "6%"] as const;
type ZigzagOption = (typeof ZIGZAG_OPTIONS)[number];
const TREND_OPTIONS = ["Off", "On"] as const;
type TrendOption = (typeof TREND_OPTIONS)[number];
const ZIGZAG_KEY = "kronos:chart:zigzag";
const TREND_KEY = "kronos:chart:trend";

function stored<T extends string>(key: string, options: readonly T[], fallback: T): T {
  if (typeof window === "undefined") return fallback;
  const v = window.localStorage.getItem(key) as T | null;
  return v && options.includes(v) ? v : fallback;
}

// The chart canvas uses the operator's own chart style in every app theme — the same as
// KronosStrategies/strategies/shared/db_utils.py::format_chart and ClaudeTradingRD/plot_xau.py:
// green up / black down candles with black borders and wicks on #DBDBDB, no grid.
const CHART_STYLE = {
  bg: "#DBDBDB",
  text: "#000000",
  scaleBorder: "#B8B8B8",
  up: "#089981",
  down: "#000000",
  zigzag: "#007AFF",
  trend: "#FF9500",
  muted: "#8E8E93",
} as const;

// bullish structure in the up colour, bearish in the down colour, first high/low muted
function labelColor(label: SwingLabel): string {
  if (label === "HH" || label === "HL") return CHART_STYLE.up;
  if (label === "LH" || label === "LL") return CHART_STYLE.down;
  return CHART_STYLE.muted;
}

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
  const candlesRef = useRef<CandleData[]>([]);
  const zigzagSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  const trendSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  const markersRef = useRef<ISeriesMarkersPluginApi<Time> | null>(null);

  const [interval, setIntervalState] = useState<Interval>(() => {
    if (typeof window === "undefined") return "5m";
    const stored = window.localStorage.getItem(STORAGE_KEY) as Interval | null;
    return stored && INTERVALS.includes(stored) ? stored : "5m";
  });

  const [zigzagOpt, setZigzagOpt] = useState<ZigzagOption>(() =>
    stored(ZIGZAG_KEY, ZIGZAG_OPTIONS, "Off"),
  );
  const [trendOpt, setTrendOpt] = useState<TrendOption>(() =>
    stored(TREND_KEY, TREND_OPTIONS, "On"),
  );
  // ref so the polling fetch always draws with the current toggles
  const overlayRef = useRef({ zigzagOpt, trendOpt });
  overlayRef.current = { zigzagOpt, trendOpt };

  const drawStructure = useCallback(() => {
    const zz = zigzagSeriesRef.current;
    const tr = trendSeriesRef.current;
    const mk = markersRef.current;
    if (!zz || !tr || !mk) return;
    const { zigzagOpt: opt, trendOpt: trend } = overlayRef.current;
    const bars = candlesRef.current;
    if (opt === "Off" || bars.length < 3) {
      zz.setData([]);
      tr.setData([]);
      mk.setMarkers([]);
      return;
    }
    const pivots = zigzag(bars, parseFloat(opt));
    const labels = swingLabels(pivots);
    zz.setData(pivots.map((p) => ({ time: p.time as UTCTimestamp, value: p.price })));
    const path = trend === "On" ? hhLlPath(pivots, labels) : [];
    tr.setData(
      path.length > 1 ? path.map((p) => ({ time: p.time as UTCTimestamp, value: p.price })) : [],
    );
    const markers: SeriesMarker<Time>[] = labels.map((p) => ({
      time: p.time as UTCTimestamp,
      position: p.kind === "H" ? "aboveBar" : "belowBar",
      shape: "circle",
      size: 0.6,
      color: labelColor(p.label),
      text: p.label,
    }));
    mk.setMarkers(markers);
  }, []);

  const fetchData = useCallback(async (tf: Interval) => {
    try {
      const res = await client.query({
        query: CANDLES_QUERY,
        variables: { symbol: SYMBOL, interval: tf, limit: CANDLE_LIMIT },
        fetchPolicy: "no-cache",
      });
      const candles: CandleData[] = res.data.candles ?? [];
      candleSeriesRef.current?.setData(candles);
      candlesRef.current = candles;
      drawStructure();
      if (firstLoadRef.current && candles.length > 0) {
        chartRef.current?.timeScale().fitContent();
        firstLoadRef.current = false;
      }
    } catch (err: any) {
      toast.error(err.message);
      console.error(err);
    }
  }, [drawStructure]);

  // One-time chart creation — dark defaults; theme effect applies correct colours immediately after
  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: chartContainerRef.current.clientHeight,
      layout: {
        background: { color: CHART_STYLE.bg },
        textColor: CHART_STYLE.text,
      },
      grid: {
        vertLines: { visible: false },
        horzLines: { visible: false },
      },
      rightPriceScale: { borderColor: CHART_STYLE.scaleBorder },
      timeScale: { borderColor: CHART_STYLE.scaleBorder, timeVisible: true, secondsVisible: true },
    });
    chart.applyOptions({
      rightPriceScale: { scaleMargins: { top: 0.1, bottom: 0.1 } },
      crosshair: { horzLine: { visible: false, labelVisible: false } },
    });
    chartRef.current = chart;

    candleSeriesRef.current = chart.addSeries(CandlestickSeries, {
      priceFormat: { type: "price", precision: 2, minMove: 0.01 },
      upColor: CHART_STYLE.up,
      downColor: CHART_STYLE.down,
      borderVisible: true,
      borderUpColor: CHART_STYLE.down,
      borderDownColor: CHART_STYLE.down,
      wickUpColor: CHART_STYLE.down,
      wickDownColor: CHART_STYLE.down,
    });

    zigzagSeriesRef.current = chart.addSeries(LineSeries, {
      color: CHART_STYLE.zigzag,
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: false,
      crosshairMarkerVisible: false,
    });
    trendSeriesRef.current = chart.addSeries(LineSeries, {
      color: CHART_STYLE.trend,
      lineWidth: 3,
      priceLineVisible: false,
      lastValueVisible: false,
      crosshairMarkerVisible: false,
    });
    markersRef.current = createSeriesMarkers(candleSeriesRef.current, []);

    // Legend overlay — uses CSS custom properties so it tracks theme changes automatically
    const legend = document.createElement("div");
    legend.style.position = "absolute";
    legend.style.left = "12px";
    legend.style.top = "12px";
    legend.style.zIndex = "1";
    legend.style.fontSize = "12px";
    legend.style.fontWeight = "500";
    legend.style.lineHeight = "20px";
    legend.style.color = CHART_STYLE.text;
    legend.style.backgroundColor = "rgba(255,255,255,0.72)";
    legend.style.padding = "8px 10px";
    legend.style.borderRadius = "6px";
    legend.style.border = "1px solid rgba(0,0,0,0.12)";
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
      const color = isGreen ? CHART_STYLE.up : CHART_STYLE.down;
      legend.innerHTML = `
        <div style="font-weight:600;">${SYMBOL}</div>
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
      zigzagSeriesRef.current = null;
      trendSeriesRef.current = null;
      markersRef.current = null;
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Redraw the structure overlay when a toggle changes
  useEffect(() => {
    drawStructure();
  }, [zigzagOpt, trendOpt, drawStructure]);

  // Refetch + polling whenever interval changes
  useEffect(() => {
    if (!candleSeriesRef.current) return;
    firstLoadRef.current = true;
    candleSeriesRef.current.setData([]);
    candlesRef.current = [];
    drawStructure();
    fetchData(interval);
    const id = window.setInterval(() => fetchData(interval), POLL_MS);
    return () => window.clearInterval(id);
  }, [interval, fetchData, drawStructure]);

  const onSelectZigzag = (v: ZigzagOption) => {
    setZigzagOpt(v);
    if (typeof window !== "undefined") window.localStorage.setItem(ZIGZAG_KEY, v);
  };
  const onSelectTrend = (v: TrendOption) => {
    setTrendOpt(v);
    if (typeof window !== "undefined") window.localStorage.setItem(TREND_KEY, v);
  };

  const onSelectInterval = (tf: Interval) => {
    setIntervalState(tf);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(STORAGE_KEY, tf);
    }
  };

  return (
    <div className="w-full">
      {/* Toolbar — Task 5.1 style mapping applied */}
      <div className="flex flex-wrap items-center gap-x-6 gap-y-2 mb-2">
        <ToolbarGroup label="Interval" options={INTERVALS} value={interval} onSelect={onSelectInterval} />
        <ToolbarGroup label="Zigzag" options={ZIGZAG_OPTIONS} value={zigzagOpt} onSelect={onSelectZigzag} />
        <ToolbarGroup
          label="Trend"
          options={TREND_OPTIONS}
          value={trendOpt}
          onSelect={onSelectTrend}
          disabled={zigzagOpt === "Off"}
          title={zigzagOpt === "Off" ? "Turn the zigzag on to draw the HH–LL trend line" : undefined}
        />
      </div>
      <div className="relative w-full h-[80vh]">
        <div ref={chartContainerRef} className="w-full h-full" />
      </div>
    </div>
  );
};

function ToolbarGroup<T extends string>({
  label,
  options,
  value,
  onSelect,
  disabled = false,
  title,
}: {
  label: string;
  options: readonly T[];
  value: T;
  onSelect: (v: T) => void;
  disabled?: boolean;
  title?: string;
}) {
  return (
    <div
      className="flex items-center gap-2"
      role="radiogroup"
      aria-label={label}
      title={title}
      style={disabled ? { opacity: 0.5 } : undefined}
    >
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
        {label}:
      </span>
      {options.map((opt) => {
        const active = opt === value;
        return (
          <button
            key={opt}
            type="button"
            role="radio"
            aria-checked={active}
            disabled={disabled}
            onClick={() => onSelect(opt)}
            className={
              active
                ? "px-3 py-1 text-sm transition-colors bg-[var(--tv-accent)] hover:bg-[var(--tv-accent-hover)]"
                : "px-3 py-1 text-sm transition-colors bg-[var(--tv-surface)] hover:bg-[var(--tv-surface-2)]"
            }
            style={
              active
                ? { color: "#fff", borderRadius: "6px" }
                : {
                    color: "var(--tv-text-2)",
                    borderRadius: "6px",
                    border: "1px solid var(--tv-border)",
                  }
            }
          >
            {opt}
          </button>
        );
      })}
    </div>
  );
}

export default CandleChart;
