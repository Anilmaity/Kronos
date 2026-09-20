/* eslint-disable react-hooks/exhaustive-deps */
"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";

// Libs
import { toast } from "sonner";

// GraphQL
import { client } from "@/GraphQL/client";
import { middleware } from "@/GraphQL/middleware";
import {
  STRATEGY_MANAGER_STATE,
  REGIME_HISTORY,
  SET_MANAGER_MODE,
  ARM_STRATEGY,
  UPDATE_MANAGER_CONFIG,
} from "@/GraphQL/managerControls";

// Utils
import { formatCapital } from "@/utils/FormatCapital";
import { fmtDateTime, fmtNumber } from "@/utils/format";

// Components
import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

// Lib
import { panelStyle } from "@/lib/tvStyles";

/* ------------------------------------------------------------------ */
/* Types                                                               */
/* ------------------------------------------------------------------ */

interface ManagerConfig {
  id: string;
  masterMode: "ON" | "OFF";
  killSwitchLossUsd: string; // GraphQL Decimal arrives as string
  maxConcurrentPositions: number;
  state: string; // JSONString
  modifiedAt: string;
}

interface ManagedStrategy {
  id: string;
  slot: string;
  policyKey: string;
  policyParams: string; // JSONString
  armMode: "OFF" | "PAPER" | "LIVE";
  liveEligible: boolean;
  desiredActive: boolean;
  lastReason: string;
  lastEvaluatedAt: string | null;
  strategyName: string | null;
  todayPnl: number | null;
  openPositions: number | null;
  userStrategy: {
    id: string;
    name: string;
    brokerName: string | null;
    isActive: boolean;
    deployed: boolean;
  };
}

interface RegimeSnapshot {
  id: string;
  createdAt: string;
  symbol: string;
  d1Bias: string;
  h4Bias: string;
  volRegime: "LOW" | "NORMAL" | "HIGH" | "EXTREME";
  trendRegime: "TRENDING" | "RANGING" | "MIXED";
  session: "ASIA" | "LONDON" | "NY" | "OVERLAP" | "ROLLOVER";
  marketClosed: boolean;
  details: string; // JSONString
}

interface RegimeHistoryPoint {
  id: string;
  createdAt: string;
  d1Bias: string;
  h4Bias: string;
  volRegime: RegimeSnapshot["volRegime"];
  trendRegime: RegimeSnapshot["trendRegime"];
  session: RegimeSnapshot["session"];
  marketClosed: boolean;
}

interface ManagerAction {
  id: string;
  createdAt: string;
  action: "START" | "PAUSE" | "KILL_SWITCH" | "INFO";
  reason: string;
  managedStrategy: {
    id: string;
    slot: string;
    strategyName: string | null;
  } | null;
}

/* ------------------------------------------------------------------ */
/* Styling helpers (Algorobos tokens — matches the Archive tab)        */
/* ------------------------------------------------------------------ */

const labelStyle: React.CSSProperties = {
  fontSize: "11px",
  fontWeight: 500,
  letterSpacing: "0.4px",
  textTransform: "uppercase",
  color: "var(--tv-text-3)",
};

const smallMono: React.CSSProperties = {
  fontSize: "11px",
  letterSpacing: "0.3px",
  textTransform: "uppercase",
  color: "var(--tv-text-3)",
};

const chipBase: React.CSSProperties = {
  fontSize: "11px",
  fontWeight: 600,
  borderRadius: "4px",
  padding: "3px 10px",
  border: "1px solid var(--tv-border)",
};

/* ------------------------------------------------------------------ */
/* Pure helpers                                                        */
/* ------------------------------------------------------------------ */

const parseJson = (raw: string | null | undefined): Record<string, any> => {
  if (!raw) return {};
  try {
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
};

const biasClass = (bias: string): string => {
  const b = (bias || "").toLowerCase();
  if (b === "bullish" || b === "long") return "text-market-up";
  if (b === "bearish" || b === "short") return "text-market-down";
  return "text-ink-faint";
};

const volColor = (vol: string): string => {
  switch (vol) {
    case "LOW":
      return "var(--tv-text-3)";
    case "NORMAL":
      return "var(--tv-up)";
    case "HIGH":
      return "var(--tv-warn)";
    case "EXTREME":
      return "var(--tv-down)";
    default:
      return "var(--tv-text-3)";
  }
};

const actionColor = (action: ManagerAction["action"]): string => {
  switch (action) {
    case "START":
      return "var(--tv-up)";
    case "PAUSE":
      return "var(--tv-warn)";
    case "KILL_SWITCH":
      return "var(--tv-down)";
    default:
      return "var(--tv-text-3)";
  }
};

// Kill-switch trip is stored in ManagerConfig.state JSON by the manager loop.
const killSwitchTripped = (state: Record<string, any>): boolean => {
  return Object.entries(state).some(
    ([key, value]) => /kill|trip/i.test(key) && !!value
  );
};

/* ------------------------------------------------------------------ */
/* Component                                                           */
/* ------------------------------------------------------------------ */

const ManagerPage = () => {
  const [config, setConfig] = useState<ManagerConfig | null>(null);
  const [strategies, setStrategies] = useState<ManagedStrategy[]>([]);
  const [regime, setRegime] = useState<RegimeSnapshot | null>(null);
  const [actions, setActions] = useState<ManagerAction[]>([]);
  const [history, setHistory] = useState<RegimeHistoryPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadFailed, setLoadFailed] = useState(false);

  // Master-mode confirm dialog
  const [pendingMode, setPendingMode] = useState<"ON" | "OFF" | null>(null);

  // Config dialog
  const [configOpen, setConfigOpen] = useState(false);
  const [killSwitchInput, setKillSwitchInput] = useState("");
  const [maxPosInput, setMaxPosInput] = useState("");
  const [savingConfig, setSavingConfig] = useState(false);

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchState = useCallback(async () => {
    try {
      const { data } = await client.query({
        query: STRATEGY_MANAGER_STATE,
        fetchPolicy: "no-cache",
      });
      setConfig(data.managerConfig ?? null);
      setStrategies(data.managedStrategies ?? []);
      setRegime(data.latestRegime ?? null);
      setActions(data.managerActions ?? []);
      setLoadFailed(false);
    } catch (err) {
      setLoadFailed(true);
      middleware(err);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchHistory = useCallback(async () => {
    try {
      const { data } = await client.query({
        query: REGIME_HISTORY,
        variables: { symbol: "XAU_USD", hours: 24 },
        fetchPolicy: "no-cache",
      });
      setHistory(data.regimeHistory ?? []);
    } catch (err) {
      // History strip is decorative — don't spam a second toast on the
      // same failure; the state query error already surfaced.
      console.error(err);
    }
  }, []);

  useEffect(() => {
    fetchState();
    fetchHistory();
    pollRef.current = setInterval(() => {
      fetchState();
      fetchHistory();
    }, 30_000);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  /* ------------------------------ mutations ------------------------ */

  const confirmSetMode = () => {
    if (!pendingMode) return;
    const mode = pendingMode;
    setPendingMode(null);
    client
      .mutate({
        mutation: SET_MANAGER_MODE,
        variables: { masterMode: mode },
        fetchPolicy: "no-cache",
      })
      .then((response) => {
        const message = response.data.SetManagerMode.Response;
        if (message === "Success") {
          toast.success(`Manager ${mode === "ON" ? "enabled" : "disabled"}`);
          fetchState();
        } else {
          toast.error(message);
        }
      })
      .catch((err) => {
        middleware(err);
      });
  };

  const handleArm = (managedStrategyId: string, armMode: string) => {
    client
      .mutate({
        mutation: ARM_STRATEGY,
        variables: { managedStrategyId, armMode },
        fetchPolicy: "no-cache",
      })
      .then((response) => {
        const message = response.data.ArmStrategy.Response;
        if (message === "Success") {
          toast.success(`Armed ${armMode}`);
        } else {
          toast.error(message);
        }
        fetchState();
      })
      .catch((err) => {
        middleware(err);
      });
  };

  const openConfigDialog = () => {
    setKillSwitchInput(
      config ? String(Number(config.killSwitchLossUsd)) : ""
    );
    setMaxPosInput(config ? String(config.maxConcurrentPositions) : "");
    setConfigOpen(true);
  };

  const handleSaveConfig = () => {
    const killSwitch = Number(killSwitchInput);
    const maxPos = Number(maxPosInput);
    if (!isFinite(killSwitch) || killSwitch <= 0) {
      toast.error("Kill-switch loss must be a positive dollar amount");
      return;
    }
    if (!Number.isInteger(maxPos) || maxPos < 1) {
      toast.error("Max concurrent positions must be an integer of at least 1");
      return;
    }
    setSavingConfig(true);
    client
      .mutate({
        mutation: UPDATE_MANAGER_CONFIG,
        variables: {
          killSwitchLossUsd: killSwitch,
          maxConcurrentPositions: maxPos,
        },
        fetchPolicy: "no-cache",
      })
      .then((response) => {
        const message = response.data.UpdateManagerConfig.Response;
        if (message === "Success") {
          toast.success("Manager config updated");
          setConfigOpen(false);
          fetchState();
        } else {
          toast.error(message);
        }
      })
      .catch((err) => {
        middleware(err);
      })
      .finally(() => {
        setSavingConfig(false);
      });
  };

  /* ------------------------------ derived -------------------------- */

  const managerOn = config?.masterMode === "ON";
  const configState = parseJson(config?.state);
  const tripped = killSwitchTripped(configState);
  const details = parseJson(regime?.details);
  const detailEntries = Object.entries(details)
    .filter(([, v]) => typeof v === "number" || typeof v === "string")
    .slice(0, 8);

  const pnlCell = (value: number | null | undefined) => {
    const v = Number(value ?? 0);
    const cls = v < 0 ? "text-down" : "text-up";
    return (
      <span className={`font-semibold tnum ${cls}`}>
        {formatCapital(Number(v.toFixed(2)))}
      </span>
    );
  };

  /* ------------------------------ render --------------------------- */

  if (loading) {
    return (
      <div className="flex flex-col items-start w-full gap-6">
        <span style={labelStyle}>07 — Strategy Manager</span>
        <div style={{ ...labelStyle, letterSpacing: "0.22em", padding: "40px" }}>
          ◆ Loading…
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-start w-full gap-6">
      {/* Top bar */}
      <div className="flex items-center justify-between w-full gap-4 flex-wrap">
        <span style={labelStyle}>07 — Strategy Manager</span>
        {regime && (
          <span style={smallMono}>
            Regime as of {fmtDateTime(regime.createdAt)} · {regime.symbol}
          </span>
        )}
      </div>

      {loadFailed && !config ? (
        <div
          className="w-full flex items-center justify-center px-4 py-16"
          style={{
            ...panelStyle,
            fontSize: 13,
            color: "var(--tv-text-3)",
          }}
        >
          Could not reach the strategy manager — retrying every 30 seconds
        </div>
      ) : (
        <>
          {/* ── 1. Master bar ─────────────────────────────────────── */}
          <div
            className="w-full flex items-center justify-between gap-6 px-4 py-4 flex-wrap"
            style={panelStyle}
          >
            <div className="flex items-center gap-4">
              <Switch
                checked={managerOn}
                onCheckedChange={(checked) =>
                  setPendingMode(checked ? "ON" : "OFF")
                }
              />
              <div className="flex flex-col">
                <span
                  className="text-base font-semibold"
                  style={{ color: managerOn ? "var(--tv-up)" : "var(--tv-text-3)" }}
                >
                  Manager {managerOn ? "ON" : "OFF"}
                </span>
                <span style={smallMono}>
                  {managerOn
                    ? "Gating armed strategies by regime"
                    : "Observing only — flips nothing"}
                </span>
              </div>
            </div>

            <div className="flex items-center gap-8 flex-wrap">
              <div className="flex flex-col items-start">
                <span style={smallMono}>Kill-switch</span>
                <span className="font-semibold">
                  −${config ? Number(config.killSwitchLossUsd).toFixed(0) : "—"}
                  /day
                </span>
              </div>
              <div className="flex flex-col items-start">
                <span style={smallMono}>Max concurrent</span>
                <span className="font-semibold">
                  {config?.maxConcurrentPositions ?? "—"} positions
                </span>
              </div>
              <div className="flex flex-col items-start">
                <span style={smallMono}>Status</span>
                <span
                  className="font-semibold"
                  style={{ color: tripped ? "var(--tv-down)" : "var(--tv-up)" }}
                >
                  {tripped ? "KILL-SWITCH TRIPPED" : "Nominal"}
                </span>
              </div>
              <Button
                variant="outline"
                onClick={openConfigDialog}
                style={{
                  ...smallMono,
                  border: "1px solid var(--tv-border)",
                  borderRadius: "6px",
                }}
              >
                Configure
              </Button>
            </div>
          </div>

          {/* ── 2. Regime panel ───────────────────────────────────── */}
          <div className="w-full flex flex-col gap-4 px-4 py-4" style={panelStyle}>
            <span style={labelStyle}>Regime — XAU_USD</span>
            {!regime ? (
              <div
                style={{
                  fontSize: 13,
                  color: "var(--tv-text-3)",
                }}
              >
                No regime snapshots yet — the manager service has not reported.
              </div>
            ) : (
              <>
                <div className="flex items-center gap-3 flex-wrap">
                  <span style={chipBase} className={biasClass(regime.d1Bias)}>
                    D1 · {regime.d1Bias}
                  </span>
                  <span style={chipBase} className={biasClass(regime.h4Bias)}>
                    H4 · {regime.h4Bias}
                  </span>
                  <span
                    style={{
                      ...chipBase,
                      color: volColor(regime.volRegime),
                      borderColor: volColor(regime.volRegime),
                    }}
                  >
                    Vol · {regime.volRegime}
                  </span>
                  <span style={{ ...chipBase, color: "var(--tv-text-2)" }}>
                    {regime.trendRegime}
                  </span>
                  <span style={{ ...chipBase, color: "var(--tv-text-2)" }}>
                    Session · {regime.session}
                  </span>
                  {regime.marketClosed && (
                    <span
                      style={{
                        ...chipBase,
                        color: "var(--tv-down)",
                        borderColor: "var(--tv-down)",
                      }}
                    >
                      Market closed
                    </span>
                  )}
                </div>

                {detailEntries.length > 0 && (
                  <div className="flex items-center gap-6 flex-wrap">
                    {detailEntries.map(([key, value]) => (
                      <div key={key} className="flex flex-col items-start">
                        <span style={smallMono}>{key.replace(/_/g, " ")}</span>
                        <span
                          className="text-sm"
                          style={{
                            color: "var(--tv-text-2)",
                          }}
                        >
                          {fmtNumber(value)}
                        </span>
                      </div>
                    ))}
                  </div>
                )}

                {/* Mini 24h history strip (colored by vol regime) */}
                {history.length > 0 && (
                  <div className="flex flex-col gap-1 w-full">
                    <span style={smallMono}>Last 24h · vol regime</span>
                    <div className="flex items-end gap-[2px] w-full overflow-hidden h-6">
                      {history.map((h) => (
                        <div
                          key={h.id}
                          title={`${fmtDateTime(h.createdAt)} · ${h.volRegime} · ${h.trendRegime} · ${h.session}`}
                          style={{
                            width: "4px",
                            minWidth: "2px",
                            height:
                              h.volRegime === "EXTREME"
                                ? "24px"
                                : h.volRegime === "HIGH"
                                ? "18px"
                                : h.volRegime === "NORMAL"
                                ? "12px"
                                : "7px",
                            background: volColor(h.volRegime),
                            opacity: h.marketClosed ? 0.25 : 0.9,
                          }}
                        />
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>

          {/* ── 3. Strategy cards ─────────────────────────────────── */}
          <div className="w-full flex flex-col gap-3">
            <span style={labelStyle}>Managed strategies</span>
            {strategies.length === 0 ? (
              <div
                className="w-full flex items-center justify-center px-4 py-16"
                style={{
                  ...panelStyle,
                  fontSize: 13,
                  color: "var(--tv-text-3)",
                }}
              >
                No managed strategies configured
              </div>
            ) : (
              <div className="w-full grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                {strategies.map((s) => {
                  const running = s.userStrategy?.isActive;
                  return (
                    <div
                      key={s.id}
                      className="flex flex-col gap-3 px-4 py-4"
                      style={panelStyle}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex flex-col">
                          <span className="text-base font-semibold text-ink">
                            {s.strategyName || s.userStrategy?.name || "—"}
                          </span>
                          <span style={smallMono}>
                            {s.slot}
                            {s.userStrategy?.brokerName
                              ? ` · ${s.userStrategy.brokerName}`
                              : ""}
                          </span>
                        </div>
                        <span
                          style={{
                            ...chipBase,
                            color: running ? "var(--tv-up)" : "var(--tv-text-3)",
                            borderColor: running
                              ? "var(--tv-up)"
                              : "var(--tv-border)",
                          }}
                        >
                          {running ? "Running" : "Paused"}
                        </span>
                      </div>

                      <div className="flex items-center gap-3">
                        <Select
                          value={s.armMode}
                          onValueChange={(mode) => {
                            if (mode !== s.armMode) handleArm(s.id, mode);
                          }}
                        >
                          <SelectTrigger className="w-[110px] h-8">
                            <SelectValue placeholder={s.armMode} />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="OFF">OFF</SelectItem>
                            <SelectItem value="PAPER">PAPER</SelectItem>
                            <SelectItem value="LIVE" disabled={!s.liveEligible}>
                              LIVE
                            </SelectItem>
                          </SelectContent>
                        </Select>
                        {!s.liveEligible && (
                          <TooltipProvider>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <span
                                  style={{
                                    ...chipBase,
                                    color: "var(--tv-warn)",
                                    borderColor: "var(--tv-warn)",
                                    cursor: "default",
                                  }}
                                >
                                  Paper ceiling
                                </span>
                              </TooltipTrigger>
                              <TooltipContent>
                                <p className="max-w-[240px]">
                                  Not live-eligible: no positive held-out
                                  backtest verdict yet. PAPER is the ceiling.
                                </p>
                              </TooltipContent>
                            </Tooltip>
                          </TooltipProvider>
                        )}
                      </div>

                      <div className="flex items-center justify-between gap-4">
                        <div className="flex flex-col">
                          <span style={smallMono}>Today P&amp;L</span>
                          {pnlCell(s.todayPnl)}
                        </div>
                        <div className="flex flex-col">
                          <span style={smallMono}>Open positions</span>
                          <span className="font-semibold tnum text-center">
                            {s.openPositions ?? 0}
                          </span>
                        </div>
                        <div className="flex flex-col">
                          <span style={smallMono}>Policy</span>
                          <span
                            className="text-sm"
                            style={{
                              color: "var(--tv-text-2)",
                            }}
                          >
                            {s.policyKey || "—"}
                          </span>
                        </div>
                      </div>

                      <div
                        className="w-full pt-2"
                        style={{ borderTop: "1px solid var(--tv-border)" }}
                      >
                        <span
                          style={{
                            fontSize: 13,
                            color: "var(--tv-text-3)",
                          }}
                        >
                          {s.lastReason || "Not evaluated yet"}
                        </span>
                        <div style={{ ...smallMono, marginTop: "2px" }}>
                          Evaluated {fmtDateTime(s.lastEvaluatedAt)}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* ── 4. Action log ─────────────────────────────────────── */}
          <div className="w-full flex flex-col gap-3">
            <span style={labelStyle}>Action log</span>
            {actions.length === 0 ? (
              <div
                className="w-full flex items-center justify-center px-4 py-10"
                style={{
                  ...panelStyle,
                  fontSize: 13,
                  color: "var(--tv-text-3)",
                }}
              >
                No manager actions recorded yet
              </div>
            ) : (
              <div
                className="w-full flex flex-col items-start justify-start overflow-x-auto"
                style={panelStyle}
              >
                <div
                  className="flex items-center w-full px-4 py-3 min-w-[720px]"
                  style={{
                    borderBottom: "1px solid var(--tv-border)",
                    fontSize: "11px",
                    letterSpacing: "0.4px",
                    textTransform: "uppercase",
                    color: "var(--tv-text-3)",
                    fontWeight: 500,
                  }}
                >
                  <div className="w-1/6">Time</div>
                  <div className="w-1/6 text-center">Action</div>
                  <div className="w-1/4">Strategy</div>
                  <div className="w-5/12">Reason</div>
                </div>
                {actions.map((a) => (
                  <div
                    key={a.id}
                    className="flex items-center w-full border-b py-2 min-w-[720px] px-4 text-sm"
                  >
                    <div
                      className="w-1/6"
                      style={{ fontFamily: "var(--font-mono, monospace)" }}
                    >
                      {fmtDateTime(a.createdAt)}
                    </div>
                    <div className="w-1/6 flex justify-center">
                      <span
                        style={{
                          ...chipBase,
                          color: actionColor(a.action),
                          borderColor: actionColor(a.action),
                        }}
                      >
                        {a.action.replace("_", " ")}
                      </span>
                    </div>
                    <div className="w-1/4 font-semibold">
                      {a.managedStrategy
                        ? a.managedStrategy.strategyName ||
                          a.managedStrategy.slot
                        : "—"}
                    </div>
                    <div className="w-5/12" style={{ color: "var(--tv-text-2)" }}>
                      {a.reason || "—"}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}

      {/* Master mode confirm dialog */}
      <AlertDialog
        open={pendingMode !== null}
        onOpenChange={(open) => {
          if (!open) setPendingMode(null);
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              Turn manager {pendingMode === "ON" ? "ON" : "OFF"}?
            </AlertDialogTitle>
            <AlertDialogDescription>
              {pendingMode === "ON"
                ? "The manager will start pausing and resuming armed strategies according to their regime policies. Strategies armed OFF are never touched."
                : "The manager will stop managing. Strategies keep their current running state; the regime engine keeps recording snapshots."}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={confirmSetMode}>
              {pendingMode === "ON" ? "Turn ON" : "Turn OFF"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Kill-switch / config dialog */}
      <Dialog open={configOpen} onOpenChange={setConfigOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Manager configuration</DialogTitle>
            <DialogDescription>
              Global guards applied across all managed strategies.
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-4 py-2">
            <div className="flex flex-col gap-1">
              <label style={smallMono}>Daily kill-switch loss (USD)</label>
              <Input
                type="number"
                min={1}
                step="1"
                value={killSwitchInput}
                onChange={(e) => setKillSwitchInput(e.target.value)}
                placeholder="150"
              />
            </div>
            <div className="flex flex-col gap-1">
              <label style={smallMono}>Max concurrent open positions</label>
              <Input
                type="number"
                min={1}
                step="1"
                value={maxPosInput}
                onChange={(e) => setMaxPosInput(e.target.value)}
                placeholder="3"
              />
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setConfigOpen(false)}
              disabled={savingConfig}
            >
              Cancel
            </Button>
            <Button onClick={handleSaveConfig} disabled={savingConfig}>
              {savingConfig ? "Saving…" : "Save"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default ManagerPage;
