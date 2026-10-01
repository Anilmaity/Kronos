"use client";
// Popups for the Telegram copy-trade tabs (Neymar / Neymar VIP):
//   AddCopyTradeDialog — "Add Data": put another broker account on the tab
//   PriceDialog        — change an account's fixed lot ("Price")
// The copy-trader trades every account on the tab at its Price — the TOTAL lot
// per signal, split evenly across the signal's TP legs (min 0.01 per leg).
import React, { useEffect, useState } from "react";
import { toast } from "sonner";

import { client } from "@/GraphQL/client";
import { middleware } from "@/GraphQL/middleware";
import {
  ADD_COPY_TRADE_ACCOUNT,
  GET_COPY_TRADE_ACCOUNT_OPTIONS,
  SET_COPY_TRADE_LOT,
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
  userstrategys: { id: string; strategy: { id: string } | null }[];
}

const LOT_HELP =
  "Total lot per signal, split across the signal's TP legs (e.g. 0.1 with 3 TPs = 3 × 0.03). Minimum 0.01 per leg.";

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
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    setBrokerId("");
    setLot("0.1");
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

  const err = lotError(lot);
  const canSave = Boolean(brokerId) && !err && !saving;

  const save = () => {
    if (!canSave) return;
    setSaving(true);
    client
      .mutate({
        mutation: ADD_COPY_TRADE_ACCOUNT,
        variables: { source, userBrokerId: brokerId, lotSize: Number(lot) },
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
      <DialogContent>
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
