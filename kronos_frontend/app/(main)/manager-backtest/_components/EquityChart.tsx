"use client";

import React, { useEffect, useRef } from "react";

import { useTheme } from "next-themes";
import {
  createChart,
  IChartApi,
  LineSeries,
  UTCTimestamp,
} from "lightweight-charts";

interface Props {
  gated: [string, number][];
  ungated?: [string, number][];
}

// lightweight-charts needs concrete colors (no CSS vars); keep these in step
// with the globals.css token values for each theme.
const CHART_THEME = {
  dark: { text: "#7C8090", grid: "#262B38", up: "#089981", soft: "#7C8090" },
  light: { text: "#85888F", grid: "#E7E8EE", up: "#089981", soft: "#85888F" },
};

const toSeries = (points: [string, number][]) => {
  // Cumulative-equity points keyed by exit time. Lightweight-charts requires
  // strictly ascending unique timestamps: collapse same-second exits to the
  // last value.
  const bySec = new Map<number, number>();
  for (const [iso, cum] of points) {
    bySec.set(Math.floor(new Date(iso).getTime() / 1000), cum);
  }
  return Array.from(bySec.entries())
    .sort((a, b) => a[0] - b[0])
    .map(([t, value]) => ({ time: t as UTCTimestamp, value }));
};

const EquityChart = ({ gated, ungated }: Props) => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const { resolvedTheme } = useTheme();

  useEffect(() => {
    if (!containerRef.current) return;
    const palette =
      CHART_THEME[resolvedTheme === "light" ? "light" : "dark"];

    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height: 260,
      layout: {
        background: { color: "transparent" },
        textColor: palette.text,
      },
      grid: {
        vertLines: { color: palette.grid },
        horzLines: { color: palette.grid },
      },
      timeScale: { borderColor: palette.grid, timeVisible: true },
      rightPriceScale: { borderColor: palette.grid },
    });
    chartRef.current = chart;

    const gatedSeries = chart.addSeries(LineSeries, {
      color: palette.up,
      lineWidth: 2,
      title: "gated",
      priceFormat: { type: "price", precision: 1, minMove: 0.1 },
    });
    gatedSeries.setData(toSeries(gated));

    if (ungated && ungated.length > 0) {
      const ungatedSeries = chart.addSeries(LineSeries, {
        color: palette.soft,
        lineWidth: 1,
        title: "ungated",
        priceFormat: { type: "price", precision: 1, minMove: 0.1 },
      });
      ungatedSeries.setData(toSeries(ungated));
    }

    chart.timeScale().fitContent();

    const onResize = () => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth });
      }
    };
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("resize", onResize);
      chart.remove();
      chartRef.current = null;
    };
  }, [gated, ungated, resolvedTheme]);

  return <div ref={containerRef} className="w-full" />;
};

export default EquityChart;
