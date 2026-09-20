"use client";

import React, { useEffect, useState } from "react";
import { toast } from "sonner";

import { client } from "@/GraphQL/client";
import { middleware } from "@/GraphQL/middleware";
import { formatCapital } from "@/utils/FormatCapital";
import { Button } from "@/components/ui/button";
import {
  DEPLOY_STRATEGY,
  GET_MARKETPLACE,
  GET_ACCOUNTS_WITH_DEPLOYMENTS,
} from "@/GraphQL/marketplaceControls";
import { panelStyle, soft, fieldStyle } from "@/lib/tvStyles";

interface Strategy {
  id: string;
  name: string;
  description: string;
  capitalRequired: string;
  symbol: string;
  isActive: boolean;
}

interface Account {
  id: string;
  label: string;
  deployedStrategyIds: string[];
}


const MarketplaceManager: React.FC = () => {
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [openFor, setOpenFor] = useState<string | null>(null);
  const [pickedAccount, setPickedAccount] = useState<string>("");
  const [multiplier, setMultiplier] = useState<number>(1);

  const loadStrategies = () => {
    client
      .query({ query: GET_MARKETPLACE, fetchPolicy: "no-cache" })
      .then((res) => {
        const all: Strategy[] = res.data?.allStrategy ?? [];
        setStrategies(all.filter((s) => s.isActive));
      })
      .catch((err) => middleware(err));
  };

  const loadAccounts = () => {
    client
      .query({ query: GET_ACCOUNTS_WITH_DEPLOYMENTS, fetchPolicy: "no-cache" })
      .then((res) => {
        const brokers = res.data?.getuserdata?.userbrokers ?? [];
        setAccounts(
          brokers.map(
            (b: {
              id: string;
              label: string;
              userstrategys: { strategy: { id: string } }[];
            }) => ({
              id: b.id,
              label: b.label,
              deployedStrategyIds: (b.userstrategys ?? []).map(
                (us) => us.strategy?.id
              ),
            })
          )
        );
      })
      .catch((err) => middleware(err));
  };

  useEffect(() => {
    loadStrategies();
    loadAccounts();
  }, []);

  const openDeploy = (strategyId: string) => {
    setOpenFor(strategyId);
    setPickedAccount("");
    setMultiplier(1);
  };

  const handleDeploy = (strategyId: string) => {
    if (!pickedAccount) {
      toast.error("Pick an account");
      return;
    }
    client
      .mutate({
        mutation: DEPLOY_STRATEGY,
        variables: {
          strategyId,
          userBrokerId: pickedAccount,
          quantity: multiplier,
        },
        fetchPolicy: "no-cache",
      })
      .then((res) => {
        const resp = res.data.AddStrategy.Response;
        if (resp === "Success") {
          toast.success("Strategy deployed");
          setOpenFor(null);
          loadAccounts();
        } else {
          toast.error(resp);
        }
      })
      .catch((err) => middleware(err));
  };

  return (
    <div className="flex flex-col items-start w-full gap-6">
      <div className="flex flex-col">
        <span className="text-base font-semibold">Marketplace</span>
        <span className="text-sm" style={soft}>
          Deployable strategies
        </span>
      </div>

      <div
        className="w-full px-4 py-3 text-sm"
        style={{
          ...panelStyle,
          ...soft,
          borderLeft: "3px solid var(--tv-accent)",
        }}
      >
        Deployed strategies trade on the configured runner account until
        per-account trading is enabled. The account you choose here records the
        deployment but does not yet route trades.
      </div>

      {accounts.length === 0 && (
        <div className="text-sm" style={soft}>
          No accounts yet — add one on the Accounts page first.
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 w-full">
        {strategies.length === 0 && (
          <div className="text-sm" style={soft}>
            No strategies available.
          </div>
        )}
        {strategies.map((s) => (
          <div key={s.id} className="p-4 flex flex-col gap-2" style={panelStyle}>
            <div className="font-semibold">{s.name}</div>
            <div className="text-sm" style={soft}>
              {s.description || "—"}
            </div>
            <div className="text-xs" style={soft}>
              {s.symbol} · Capital {formatCapital(parseInt(s.capitalRequired))}
            </div>

            {openFor === s.id ? (
              <div className="flex flex-col gap-2 mt-2">
                <select
                  style={fieldStyle}
                  value={pickedAccount}
                  onChange={(e) => setPickedAccount(e.target.value)}
                >
                  <option value="">Select account…</option>
                  {accounts.map((a) => {
                    const already = a.deployedStrategyIds.includes(s.id);
                    return (
                      <option key={a.id} value={a.id} disabled={already}>
                        {a.label || "(no label)"}
                        {already ? " — Deployed" : ""}
                      </option>
                    );
                  })}
                </select>
                <input
                  style={fieldStyle}
                  type="number"
                  min={1}
                  value={multiplier}
                  onChange={(e) =>
                    setMultiplier(Math.max(1, Number(e.target.value)))
                  }
                />
                <div className="flex gap-2">
                  <Button size="sm" onClick={() => handleDeploy(s.id)}>
                    Confirm deploy
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => setOpenFor(null)}
                  >
                    Cancel
                  </Button>
                </div>
              </div>
            ) : (
              <div className="mt-2">
                <Button size="sm" onClick={() => openDeploy(s.id)}>
                  Deploy
                </Button>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default MarketplaceManager;
