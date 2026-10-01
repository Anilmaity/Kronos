"use client";
// Popups for the Telegram copy-trade tabs (Neymar / Neymar VIP):
//   AddCopyTradeDialog — "Add Data": put another broker account on the tab
//   PriceDialog        — change an account's fixed lot ("Price")
//   RiskDialog         — Trade SL + the account's Daily / Max drawdown
// The copy-trader trades every account on the tab at its Price — the TOTAL lot
// per signal, split evenly across the signal's TP legs (min 0.01 per leg).
import React, { useEffect, useState } from "react";
import { toast } from "sonner";

import { client } from "@/GraphQL/client";
import { middleware } from "@/GraphQL/middleware";
import {
  ADD_COPY_TRADE_ACCOUNT,
  GET_COPY_TRADE_ACCOUNT_OPTIONS,
  GET_COPY_TRADE_EQUITY,
  SET_COPY_TRADE_LOT,
  UPDATE_COPY_TRADE_RISK,
} from "@/GraphQL/strategyControls";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

import { SOURCE_STRATEGY_IDS, StrategySource } from "./strategySources";

interface BrokerOption {
  id: string;
  label: string | null;
  name: string | null;
  accountHolderName: string | null;
  metaAccountId: string | null;
  hasToken: boolean;
  isActive: boolean;
  ddEquity: string | null;
  userstrategys: { id: string; strategy: { id: string } | null }[];
}

const LOT_HELP =
  "Total lot per signal, split over its 5 trades (e.g. 0.1 = 5 × 0.02). Each trade is at least 0.01, so below 0.05 still places 5 × 0.01.";

// Mirrors the backend's parse_lot: 0.01 – 100 in steps of 0.01.
export const lotError = (raw: string): string | null => {
  const v = Number(raw);
  if (raw.trim() === "" || !Number.isFinite(v)) return "Enter a lot, e.g. 0.1";
  if (v < 0.01) return "Minimum is 0.01";
  if (v > 100) return "Maximum is 100";
  if (Math.abs(Math.round(v * 100) - v * 100) > 1e-6) return "Use steps of 0.01 (e.g. 0.1, 0.25)";
  return null;
};

const fieldStyle: React.CSSProperties = {
  width: "100%",
  height: "36px",
  padding: "0 10px",
  borderRadius: "6px",
  border: "1px solid var(--tv-border)",
  background: "var(--tv-surface)",
  color: "var(--tv-text)",
  fontSize: "13px",
};

const labelStyle: React.CSSProperties = {
  fontSize: "11px",
  fontWeight: 500,
  letterSpacing: "0.4px",
  textTransform: "uppercase",
  color: "var(--tv-text-3)",
};

const buttonStyle = (primary: boolean, disabled = false): React.CSSProperties => ({
  height: "34px",
  padding: "0 16px",
  borderRadius: "6px",
  fontSize: "13px",
  fontWeight: 600,
  border: primary ? "none" : "1px solid var(--tv-border)",
  background: primary ? "var(--tv-accent)" : "transparent",
  color: primary ? "#fff" : "var(--tv-text-2)",
  opacity: disabled ? 0.5 : 1,
  cursor: disabled ? "not-allowed" : "pointer",
});

// ── Stop loss / drawdown fields (shared by Add Data and the RiskDialog) ──────
export interface RiskForm {
  tradeSl: string;
  maxSl: string;
  dailyFloor: string;
  maxFloor: string;
  dailyOffset: string;
  maxOffset: string;
}

export const emptyRisk = (): RiskForm => ({
  tradeSl: "",
  maxSl: "90",
  dailyFloor: "",
  maxFloor: "",
  dailyOffset: "230",
  maxOffset: "500",
});

const num = (v: string): number | null => (v.trim() === "" ? null : Number(v));
const DD_BUFFER = 10;

export const riskError = (f: RiskForm, equity?: number | null): string | null => {
  const fields: [string, string][] = [
    ["Trade SL", f.tradeSl],
    ["Max SL per trade", f.maxSl],
    ["Daily drawdown", f.dailyFloor],
    ["Max drawdown", f.maxFloor],
    ["Daily reset amount", f.dailyOffset],
    ["Max reset amount", f.maxOffset],
  ];
  for (const [label, raw] of fields) {
    const v = num(raw);
    if (v !== null && (!Number.isFinite(v) || v <= 0)) return `${label} must be greater than 0`;
  }
  if (equity) {
    for (const [label, raw] of [["Daily drawdown", f.dailyFloor], ["Max drawdown", f.maxFloor]] as const) {
      const v = num(raw);
      if (v !== null && v >= equity - DD_BUFFER)
        return `${label} must be below the current equity ${equity.toFixed(2)} (minus ${DD_BUFFER})`;
    }
  }
  return null;
};

export const riskVariables = (f: RiskForm) => {
  const tradeSl = num(f.tradeSl);
  const dailyFloor = num(f.dailyFloor);
  const maxFloor = num(f.maxFloor);
  return {
    tradeSlUsd: tradeSl,
    maxSlPerTradeUsd: num(f.maxSl),
    dailyDdFloor: dailyFloor,
    maxDdFloor: maxFloor,
    dailyDdOffset: dailyFloor === null ? null : num(f.dailyOffset),
    maxDdOffset: maxFloor === null ? null : num(f.maxOffset),
  };
};

// Polls an account's equity every 3s while `active` (the copy-trader refreshes it every 3s).
export const useLiveEquity = (userBrokerId: string | undefined, active: boolean) => {
  const [equity, setEquity] = useState<number | null>(null);
  useEffect(() => {
    setEquity(null);
    if (!active || !userBrokerId) return;
    let stop = false;
    const load = () =>
      client
        .query({ query: GET_COPY_TRADE_EQUITY, fetchPolicy: "no-cache" })
        .then(({ data }) => {
          const b = (data.getuserdata?.userbrokers ?? []).find(
            (x: { id: string }) => x.id === userBrokerId
          );
          if (!stop) setEquity(b?.ddEquity ? Number(b.ddEquity) : null);
        })
        .catch(() => undefined);
    load();
    const id = setInterval(load, 3000);
    return () => {
      stop = true;
      clearInterval(id);
    };
  }, [userBrokerId, active]);
  return equity;
};

const EquityLine = ({ equity, floor }: { equity: number | null; floor: string }) => {
  if (equity === null) return null;
  const f = floor.trim() === "" ? null : Number(floor);
  const room = f !== null && Number.isFinite(f) ? equity - f : null;
  return (
    <span style={{ fontSize: "11px", color: room !== null && room <= 10 ? "var(--tv-down)" : "var(--tv-up)" }}>
      Live equity {equity.toFixed(2)}
      {room !== null ? ` · room ${room.toFixed(2)}` : ""}
    </span>
  );
};

const RiskFields = ({
  form,
  setForm,
  equity = null,
}: {
  form: RiskForm;
  setForm: (f: RiskForm) => void;
  equity?: number | null;
}) => {
  const field = (key: keyof RiskForm, label: string, placeholder: string, help?: string) => (
    <div className="flex flex-col gap-1">
      <span style={labelStyle}>{label}</span>
      <input
        type="number"
        inputMode="decimal"
        min={0}
        step={0.01}
        style={fieldStyle}
        placeholder={placeholder}
        value={form[key]}
        onChange={(e) => setForm({ ...form, [key]: e.target.value })}
      />
      {help && <span style={{ fontSize: "11px", color: "var(--tv-text-3)" }}>{help}</span>}
    </div>
  );
  return (
    <>
      <div className="grid grid-cols-2 gap-3">
        {field("tradeSl", "Trade SL (USD)", "Channel SL",
          "Total loss allowed for one signal, split across its legs. Empty = channel's SL.")}
        {field("maxSl", "Max SL per trade (USD)", "90",
          "No single trade risks more (also caps the channel's SL). A stopped trade re-enters until its share is used.")}
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div className="flex flex-col gap-1">
          {field("dailyFloor", "Daily drawdown (equity)", "Optional",
            "Equity floor for today. Reaching it closes every trade on the account.")}
          <EquityLine equity={equity} floor={form.dailyFloor} />
        </div>
        <div className="flex flex-col gap-1">
          {field("maxFloor", "Max drawdown (equity)", "Optional",
            "Overall equity floor. Reaching it closes every trade on the account.")}
          <EquityLine equity={equity} floor={form.maxFloor} />
        </div>
      </div>
      {(form.dailyFloor.trim() !== "" || form.maxFloor.trim() !== "") && (
        <div className="grid grid-cols-2 gap-3">
          {field("dailyOffset", "Daily reset (USD below equity)", "230",
            "Each new broker day: daily floor = that day's equity − this.")}
          {field("maxOffset", "Max reset (USD below equity)", "500",
            "Each new broker day: max floor = that day's equity − this.")}
        </div>
      )}
    </>
  );
};

const brokerName = (b: BrokerOption) =>
  b.label || b.name || b.accountHolderName || b.metaAccountId || b.id.slice(0, 8);

export const AddCopyTradeDialog = ({
  open,
  onOpenChange,
  source,
  nextNumber,
  onAdded,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  source: StrategySource;
  nextNumber: number;
  onAdded: () => void;
}) => {
  const [brokers, setBrokers] = useState<BrokerOption[]>([]);
  const [loading, setLoading] = useState(false);
  const [brokerId, setBrokerId] = useState("");
  const [lot, setLot] = useState("0.1");
  const [risk, setRisk] = useState<RiskForm>(emptyRisk());
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    setBrokerId("");
    setLot("0.1");
    setRisk(emptyRisk());
    setLoading(true);
    client
      .query({ query: GET_COPY_TRADE_ACCOUNT_OPTIONS, fetchPolicy: "no-cache" })
      .then(({ data }) => setBrokers(data.getuserdata?.userbrokers ?? []))
      .catch((err) => middleware(err))
      .finally(() => setLoading(false));
  }, [open]);

  // Hide accounts already on this tab.
  const tabIds = SOURCE_STRATEGY_IDS[source];
  const available = brokers.filter(
    (b) => !b.userstrategys.some((us) => us.strategy && tabIds.includes(us.strategy.id))
  );
  const usable = (b: BrokerOption) => b.isActive && Boolean(b.metaAccountId) && b.hasToken;

  const selected = brokers.find((b) => b.id === brokerId);
  const liveEquity = useLiveEquity(brokerId || undefined, open);
  const equity = liveEquity ?? (selected?.ddEquity ? Number(selected.ddEquity) : null);
  const err = lotError(lot);
  const rErr = riskError(risk, equity);
  const canSave = Boolean(brokerId) && !err && !rErr && !saving;

  const save = () => {
    if (!canSave) return;
    setSaving(true);
    client
      .mutate({
        mutation: ADD_COPY_TRADE_ACCOUNT,
        variables: { source, userBrokerId: brokerId, lotSize: Number(lot), ...riskVariables(risk) },
        fetchPolicy: "no-cache",
      })
      .then(({ data }) => {
        const res = data.AddCopyTradeAccount;
        if (res.Ok) {
          toast.success("Account added — it trades from the next signal");
          onOpenChange(false);
          onAdded();
        } else {
          toast.error(res.Response);
        }
      })
      .catch((e) => middleware(e))
      .finally(() => setSaving(false));
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Add Data</DialogTitle>
          <DialogDescription>
            Add an account to this tab. Every new signal is copied to it as XAUUSD at the Price
            (lot) you set.
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-4 py-2">
          <div className="flex flex-col gap-1">
            <span style={labelStyle}>No.</span>
            <div style={{ ...fieldStyle, display: "flex", alignItems: "center", opacity: 0.7 }}>
              {nextNumber}
            </div>
          </div>

          <div className="flex flex-col gap-1">
            <span style={labelStyle}>Account</span>
            <select
              style={fieldStyle}
              value={brokerId}
              onChange={(e) => setBrokerId(e.target.value)}
              disabled={loading}
            >
              <option value="">
                {loading
                  ? "Loading accounts…"
                  : available.length
                  ? "Select an account"
                  : "No accounts left to add"}
              </option>
              {available.map((b) => (
                <option key={b.id} value={b.id} disabled={!usable(b)}>
                  {brokerName(b)}
                  {b.metaAccountId ? ` · ${b.metaAccountId}` : ""}
                  {!b.isActive
                    ? " (inactive)"
                    : !b.metaAccountId || !b.hasToken
                    ? " (no MetaAPI token — add it in Accounts)"
                    : ""}
                </option>
              ))}
            </select>
          </div>

          <div className="flex flex-col gap-1">
            <span style={labelStyle}>Price (lot)</span>
            <input
              type="number"
              inputMode="decimal"
              min={0.01}
              step={0.01}
              style={fieldStyle}
              value={lot}
              onChange={(e) => setLot(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && save()}
            />
            <span style={{ fontSize: "12px", color: err ? "var(--tv-down)" : "var(--tv-text-3)" }}>
              {err ?? LOT_HELP}
            </span>
          </div>

          <RiskFields form={risk} setForm={setRisk} equity={equity} />
          {brokerId && equity === null && (
            <span style={{ fontSize: "12px", color: "var(--tv-text-3)" }}>
              Equity appears here once the copy-trader has read this account (new accounts: after
              they are added).
            </span>
          )}
          {rErr && <span style={{ fontSize: "12px", color: "var(--tv-down)" }}>{rErr}</span>}
        </div>

        <DialogFooter className="gap-2">
          <button style={buttonStyle(false)} onClick={() => onOpenChange(false)}>
            Cancel
          </button>
          <button style={buttonStyle(true, !canSave)} disabled={!canSave} onClick={save}>
            {saving ? "Adding…" : "Add"}
          </button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export const PriceDialog = ({
  open,
  onOpenChange,
  userStrategyId,
  accountName,
  currentLot,
  onSaved,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  userStrategyId: string;
  accountName: string;
  currentLot: string | null | undefined;
  onSaved: () => void;
}) => {
  const [lot, setLot] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open) setLot(currentLot ? String(Number(currentLot)) : "0.1");
  }, [open, currentLot]);

  const err = lotError(lot);

  const save = () => {
    if (err || saving) return;
    setSaving(true);
    client
      .mutate({
        mutation: SET_COPY_TRADE_LOT,
        variables: { userStrategyId, lotSize: Number(lot) },
        fetchPolicy: "no-cache",
      })
      .then(({ data }) => {
        const res = data.SetCopyTradeLot;
        if (res.Ok) {
          toast.success("Price updated — applies from the next signal");
          onOpenChange(false);
          onSaved();
        } else {
          toast.error(res.Response);
        }
      })
      .catch((e) => middleware(e))
      .finally(() => setSaving(false));
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Price — {accountName}</DialogTitle>
          <DialogDescription>
            {currentLot
              ? `Current: ${Number(currentLot)} lot per signal.`
              : "Currently Auto (risk-based lot). Set a Price to use a fixed lot instead."}
          </DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-1 py-2">
          <span style={labelStyle}>Price (lot)</span>
          <input
            type="number"
            inputMode="decimal"
            min={0.01}
            step={0.01}
            style={fieldStyle}
            value={lot}
            autoFocus
            onChange={(e) => setLot(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && save()}
          />
          <span style={{ fontSize: "12px", color: err ? "var(--tv-down)" : "var(--tv-text-3)" }}>
            {err ?? LOT_HELP}
          </span>
        </div>
        <DialogFooter className="gap-2">
          <button style={buttonStyle(false)} onClick={() => onOpenChange(false)}>
            Cancel
          </button>
          <button style={buttonStyle(true, Boolean(err) || saving)} disabled={Boolean(err) || saving} onClick={save}>
            {saving ? "Saving…" : "Save"}
          </button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

// "0.1 lot" for a fixed Price, "Auto" for the bot's risk-based sizing.
export const formatLot = (lotSize: string | null | undefined) =>
  lotSize ? `${Number(lotSize)} lot` : "Auto";

export const RiskDialog = ({
  open,
  onOpenChange,
  userStrategyId,
  accountName,
  initial,
  equity,
  onSaved,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  userStrategyId: string;
  accountName: string;
  initial: RiskForm;
  equity: number | null;
  onSaved: () => void;
}) => {
  const [risk, setRisk] = useState<RiskForm>(initial);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open) setRisk(initial);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const err = riskError(risk, equity);

  const save = () => {
    if (err || saving) return;
    setSaving(true);
    client
      .mutate({
        mutation: UPDATE_COPY_TRADE_RISK,
        variables: { userStrategyId, ...riskVariables(risk) },
        fetchPolicy: "no-cache",
      })
      .then(({ data }) => {
        const res = data.UpdateCopyTradeRisk;
        if (res.Ok) {
          toast.success("Stop loss & drawdown saved");
          onOpenChange(false);
          onSaved();
        } else {
          toast.error(res.Response);
        }
      })
      .catch((e) => middleware(e))
      .finally(() => setSaving(false));
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Stop Loss &amp; Drawdown — {accountName}</DialogTitle>
          <DialogDescription>
            Trade SL applies from the next signal. Drawdown floors are per MT5 account (shared by
            both Neymar tabs) and are checked every 2 seconds.
          </DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-4 py-2">
          <RiskFields form={risk} setForm={setRisk} equity={equity} />
          {err && <span style={{ fontSize: "12px", color: "var(--tv-down)" }}>{err}</span>}
        </div>
        <DialogFooter className="gap-2">
          <button style={buttonStyle(false)} onClick={() => onOpenChange(false)}>
            Cancel
          </button>
          <button style={buttonStyle(true, Boolean(err) || saving)} disabled={Boolean(err) || saving} onClick={save}>
            {saving ? "Saving…" : "Save"}
          </button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

const str = (v: string | null | undefined) => (v ? String(Number(v)) : "");

// Prefill for RiskDialog from a row + its account.
export const riskFromRow = (
  us: { tradeSlUsd?: string | null; maxSlPerTradeUsd?: string | null },
  ub: {
    dailyDdFloor?: string | null;
    maxDdFloor?: string | null;
    dailyDdOffset?: string | null;
    maxDdOffset?: string | null;
  }
): RiskForm => ({
  tradeSl: str(us.tradeSlUsd),
  maxSl: str(us.maxSlPerTradeUsd) || "90",
  dailyFloor: str(ub.dailyDdFloor),
  maxFloor: str(ub.maxDdFloor),
  dailyOffset: str(ub.dailyDdOffset) || "230",
  maxOffset: str(ub.maxDdOffset) || "500",
});

export const formatUsd = (v: string | null | undefined) =>
  v ? Number(v).toLocaleString("en-US", { maximumFractionDigits: 2 }) : "—";

// Guard status written by the copy-trader -> short label + colour.
export const ddStatusLabel = (status: string | null | undefined): { text: string; color: string } | null => {
  switch (status) {
    case "breached_daily":
      return { text: "Daily DD hit — closed", color: "var(--tv-down)" };
    case "breached_max":
      return { text: "Max DD hit — closed", color: "var(--tv-down)" };
    case "near_daily":
    case "near_max":
    case "blocked_today":
      return { text: "Blocked today", color: "var(--tv-down)" };
    case "floor_above_equity":
      return { text: "Floor ≥ equity — check", color: "var(--tv-down)" };
    default:
      return null;
  }
};

// Column widths of the copy-trade tab table (header and rows must match).
export const CT_COL = {
  no: "w-[5%]",
  name: "w-[14%]",
  open: "w-[9%]",
  price: "w-[8%]",
  tradeSl: "w-[10%]",
  daily: "w-[12%]",
  max: "w-[12%]",
  status: "w-[10%]",
  pnl: "w-[10%]",
  actions: "w-[10%]",
};
