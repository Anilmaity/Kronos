"use client";

import React, { useState } from "react";

import { toast } from "sonner";

import { client } from "@/GraphQL/client";
import { middleware } from "@/GraphQL/middleware";
import { RUN_MANAGER_BACKTEST } from "@/GraphQL/managerBacktestControls";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";

import { panelStyle } from "@/lib/tvStyles";

const labelSoft: React.CSSProperties = { color: "var(--tv-text-soft)" };

// Server-side defaults (RunManagerBacktest falls back to ManagerConfig +
// engine defaults when a field is left empty).
const PLACEHOLDERS = {
  spreadPts: "0.30",
  slippagePts: "0.10",
  lots: "0.02",
  killSwitchUsd: "150",
  maxConcurrent: "3",
  regimeCadenceMin: "5",
};

interface Props {
  onQueued: () => void;
}

const NewRunCard = ({ onQueued }: Props) => {
  const [periodStart, setPeriodStart] = useState("");
  const [periodEnd, setPeriodEnd] = useState("");
  const [label, setLabel] = useState("");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [spreadPts, setSpreadPts] = useState("");
  const [slippagePts, setSlippagePts] = useState("");
  const [lots, setLots] = useState("");
  const [killSwitchUsd, setKillSwitchUsd] = useState("");
  const [maxConcurrent, setMaxConcurrent] = useState("");
  const [regimeCadenceMin, setRegimeCadenceMin] = useState("");
  const [includeUngated, setIncludeUngated] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [inlineError, setInlineError] = useState<string | null>(null);

  const numOrNull = (s: string) => {
    if (s.trim() === "") return null;
    const n = Number(s);
    return isFinite(n) ? n : null;
  };

  const handleRun = () => {
    setInlineError(null);
    if (!periodStart || !periodEnd) {
      setInlineError("Start and end dates are required.");
      return;
    }
    setSubmitting(true);
    client
      .mutate({
        mutation: RUN_MANAGER_BACKTEST,
        variables: {
          periodStart,
          periodEnd,
          label: label.trim() || null,
          spreadPts: numOrNull(spreadPts),
          slippagePts: numOrNull(slippagePts),
          lots: numOrNull(lots),
          killSwitchUsd: numOrNull(killSwitchUsd),
          maxConcurrent:
            numOrNull(maxConcurrent) !== null
              ? Math.trunc(Number(maxConcurrent))
              : null,
          regimeCadenceMin:
            numOrNull(regimeCadenceMin) !== null
              ? Math.trunc(Number(regimeCadenceMin))
              : null,
          includeUngated,
        },
        fetchPolicy: "no-cache",
      })
      .then((response) => {
        const { ok, error } = response.data.runManagerBacktest;
        if (ok) {
          toast.success("Backtest queued");
          setLabel("");
          onQueued();
        } else {
          setInlineError(error ?? "Failed to queue backtest");
        }
      })
      .catch((err) => middleware(err))
      .finally(() => setSubmitting(false));
  };

  const advField = (
    lbl: string,
    value: string,
    setter: (v: string) => void,
    placeholder: string
  ) => (
    <div className="flex flex-col gap-1 w-[130px]">
      <span className="text-xs" style={labelSoft}>{lbl}</span>
      <Input
        value={value}
        placeholder={placeholder}
        onChange={(e) => setter(e.target.value)}
      />
    </div>
  );

  return (
    <div className="w-full flex flex-col gap-4 px-4 py-4" style={panelStyle}>
      <span className="text-sm font-semibold">New run</span>

      <div className="flex items-end gap-4 flex-wrap">
        <div className="flex flex-col gap-1">
          <span className="text-xs" style={labelSoft}>From</span>
          <Input
            type="date"
            value={periodStart}
            onChange={(e) => setPeriodStart(e.target.value)}
          />
        </div>
        <div className="flex flex-col gap-1">
          <span className="text-xs" style={labelSoft}>To</span>
          <Input
            type="date"
            value={periodEnd}
            onChange={(e) => setPeriodEnd(e.target.value)}
          />
        </div>
        <div className="flex flex-col gap-1 w-[220px]">
          <span className="text-xs" style={labelSoft}>Label (optional)</span>
          <Input
            value={label}
            placeholder="audit_&lt;from&gt;_&lt;to&gt;"
            onChange={(e) => setLabel(e.target.value)}
          />
        </div>
        <Button onClick={handleRun} disabled={submitting}>
          {submitting ? "Queueing..." : "Run backtest"}
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setShowAdvanced((v) => !v)}
        >
          {showAdvanced ? "Hide advanced" : "Advanced"}
        </Button>
      </div>

      {showAdvanced && (
        <div className="flex items-end gap-4 flex-wrap">
          {advField("Spread (pts)", spreadPts, setSpreadPts,
            PLACEHOLDERS.spreadPts)}
          {advField("Slippage (pts)", slippagePts, setSlippagePts,
            PLACEHOLDERS.slippagePts)}
          {advField("Lots", lots, setLots, PLACEHOLDERS.lots)}
          {advField("Kill-switch ($)", killSwitchUsd, setKillSwitchUsd,
            PLACEHOLDERS.killSwitchUsd)}
          {advField("Max concurrent", maxConcurrent, setMaxConcurrent,
            PLACEHOLDERS.maxConcurrent)}
          {advField("Cadence (min)", regimeCadenceMin, setRegimeCadenceMin,
            PLACEHOLDERS.regimeCadenceMin)}
          <div className="flex flex-col gap-1">
            <span className="text-xs" style={labelSoft}>Ungated arm</span>
            <div className="h-10 flex items-center">
              <Switch
                checked={includeUngated}
                onCheckedChange={setIncludeUngated}
              />
            </div>
          </div>
        </div>
      )}

      {inlineError && (
        <span className="text-sm" style={{ color: "var(--tv-down)" }}>
          {inlineError}
        </span>
      )}
    </div>
  );
};

export default NewRunCard;
