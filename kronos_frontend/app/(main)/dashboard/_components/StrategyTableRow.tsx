// React - Next default
import React, { useEffect, useState } from "react";

// Libs
import { toast } from "sonner";

// GraphQL
import { client } from "@/GraphQL/client";
import {
  CHANGE_STRATEGY_STATUS,
  SET_USER_STRATEGY_MULTIPLIER,
  EXIT_STRATEGY,
  DELETE_USER_STRATEGY,
  ARCHIVE_STRATEGY,
} from "@/GraphQL/strategyControls";

// Icons
import { IoIosMore } from "react-icons/io";
import { BsCaretDown } from "react-icons/bs";

// Utils
import { formatCapital } from "@/utils/FormatCapital";

// Hooks
import { useStrategyChangeHappend } from "@/hooks/useStrategyChangeHappend";

// Types
import { UserExchangeSetProps, UserStrategysProps } from "@/types";

// Components
import {
  Menubar,
  MenubarContent,
  MenubarItem,
  MenubarMenu,
  MenubarSeparator,
  MenubarSub,
  MenubarSubContent,
  MenubarSubTrigger,
  MenubarTrigger,
} from "@/components/ui/menubar";
import { middleware } from "@/GraphQL/middleware";
import {
  CT_COL,
  PriceDialog,
  RiskDialog,
  ddStatusLabel,
  formatLot,
  formatUsd,
  riskFromRow,
} from "./CopyTradeDialogs";

interface StrategyTableRowProps {
  index: number;
  handleExpand: (index: number) => void;
  data: UserStrategysProps;
  brokerDetails: {
    id: string;
    name: string;
    clientCode: string;
    marginAvailable: string;
    accountHolderName: string;
  };
  // Copy-trade tab layout (Neymar / Neymar VIP): no Strategy column, "Price"
  // instead of "Multiplier", and Remove (hide from the tab) as the only removal action.
  copyTrade?: boolean;
  onRemove?: () => void;
  account?: UserExchangeSetProps; // the row's MT5 account (drawdown settings)
}

const StrategyTableRow: React.FC<StrategyTableRowProps> = ({
  index,
  handleExpand,
  data,
  brokerDetails,
  copyTrade = false,
  onRemove,
  account,
}) => {
  const sizeLabel = copyTrade ? "Price" : "Multiplier";
  const [priceOpen, setPriceOpen] = useState(false);
  const [riskOpen, setRiskOpen] = useState(false);
  const equity = account?.ddEquity ? Number(account.ddEquity) : null;
  const dd = ddStatusLabel(account?.ddStatus);
  const small: React.CSSProperties = { fontSize: "11px", color: "var(--tv-text-3)", fontWeight: 500 };
  const [isActive, setIsActive] = useState<boolean>(data.isActive);

  const { setStrategyChangeHappend } = useStrategyChangeHappend();

  const totalPandL = (totalPandL: number) => {
    const totalPandLClass = totalPandL < 0 ? "text-down" : "text-up";

    return (
      <div className={`tnum font-semibold ${totalPandLClass}`}>
        {formatCapital(Number(totalPandL.toFixed(2)))}
      </div>
    );
  };

  const handleStrategyMode = ({
    strategyId,
    status,
  }: {
    strategyId: string;
    status: boolean;
  }) => {
    client
      .mutate({
        mutation: CHANGE_STRATEGY_STATUS,
        variables: { userStrategyId: strategyId, status },
        fetchPolicy: "no-cache",
      })
      .then((response) => {
        if (response.data.ChangeStrategyStatus.Response === "Success") {
          toast.success("Success in Toggle Strategy");
          setStrategyChangeHappend(true);
        } else {
          toast.error("Something went wrong in Toggle Strategy");
        }
      })
      .catch((err) => {
        middleware(err);
      });
  };

  useEffect(() => {
    setIsActive(data.isActive);
  }, [data.isActive]);

  const handleMultiplierChange = (selectedQty: string) => {
    client
      .mutate({
        mutation: SET_USER_STRATEGY_MULTIPLIER,
        variables: { userStrategyId: data.id, multiplier: Number(selectedQty) },
        fetchPolicy: "no-cache",
      })
      .then((response) => {
        if (response.data.SetUserStrategyMultiplier.Response === "Success") {
          toast.success(`${sizeLabel} Changed Successfully`);
          setStrategyChangeHappend(true);
        } else {
          toast.error(`Something went wrong in changing ${sizeLabel.toLowerCase()}`);
        }
      })
      .catch((err) => {
        middleware(err);
      });
  };

  const handleExitStrategy = ({
    strategyId,
    brokerId,
  }: {
    strategyId: string;
    brokerId: string;
  }) => {
    client
      .mutate({
        mutation: EXIT_STRATEGY,
        variables: { strategyId, brokerCredId: brokerId },
        fetchPolicy: "no-cache",
      })
      .then((response) => {
        const { Response, Ok } = response.data.ExitStrategy;
        if (Ok) {
          toast.success(Response);
        } else {
          toast.error(Response);
        }
        setStrategyChangeHappend(true);
      })
      .catch((err) => {
        middleware(err);
      });
  };

  //
  const handleDeleteStrategy = ({
    strategyId,
    brokerId,
  }: {
    strategyId: string;
    brokerId: string;
  }) => {
    // if strategy is active then exit the strategy first
    if (data.isActive) {
      handleExitStrategy({ strategyId, brokerId });
    }
    client
      .mutate({
        mutation: DELETE_USER_STRATEGY,
        variables: { id: strategyId },
        fetchPolicy: "no-cache",
      })
      .then((response) => {
        if (
          response.data.DeleteUserStrategy.Response ===
          "Strategy Deleted Successfully"
        ) {
          toast.success("Strategy Deleted Successfully");
          setStrategyChangeHappend(true);
        } else {
          toast.error("Something went wrong in delete strategy");
        }
      })
      .catch((err) => {
        middleware(err);
      });
  };

  const handleArchiveStrategy = ({ strategyId }: { strategyId: string }) => {
    client
      .mutate({
        mutation: ARCHIVE_STRATEGY,
        variables: { userStrategyId: strategyId },
        fetchPolicy: "no-cache",
      })
      .then((response) => {
        const message = response.data.ArchiveStrategy.Response;
        if (message === "Success") {
          toast.success("Strategy Archived");
          setStrategyChangeHappend(true);
        } else {
          toast.error(message);
        }
      })
      .catch((err) => {
        middleware(err);
      });
  };

  return (
    <div
      className="flex items-center justify-normal w-full font-semibold hover:bg-[var(--tv-surface-2)]"
      style={{ borderBottom: "1px solid var(--tv-border)", minHeight: "36px" }}
    >
      <div className={`tnum ${copyTrade ? CT_COL.no : "w-1/12"} text-center`}>{index + 1}</div>
      {copyTrade ? (
        <>
          <button
            className={`${CT_COL.name} cursor-pointer flex items-center gap-1 justify-between text-start`}
            onClick={() => {
              handleExpand(index);
            }}
          >
            {brokerDetails.name}
          </button>
          <div className={`tnum ${CT_COL.open} text-center`}>
            {data.activePositionsCount} | {data.totalPositionCount}
          </div>
          <div className={`tnum ${CT_COL.price} text-center`}>{formatLot(data.lotSize)}</div>
          <div className={`tnum ${CT_COL.tradeSl} text-center flex flex-col`}>
            {data.tradeSlUsd ? (
              <span>${formatUsd(data.tradeSlUsd)}</span>
            ) : (
              <span style={small}>Channel SL</span>
            )}
            <span style={small}>max ${data.maxSlPerTradeUsd ? formatUsd(data.maxSlPerTradeUsd) : "90"}/trade</span>
          </div>
          <div className={`tnum ${CT_COL.daily} text-center flex flex-col`}>
            <span>{account?.dailyDdOffset ? `$${formatUsd(account.dailyDdOffset)}` : "—"}</span>
            {account?.dailyDdFloor && <span style={small}>floor {formatUsd(account.dailyDdFloor)}</span>}
            {equity !== null && <span style={small}>equity {formatUsd(account?.ddEquity)}</span>}
          </div>
          <div className={`tnum ${CT_COL.max} text-center flex flex-col`}>
            <span>{account?.maxDdOffset ? `$${formatUsd(account.maxDdOffset)}` : "—"}</span>
            {account?.maxDdFloor && <span style={small}>floor {formatUsd(account.maxDdFloor)}</span>}
            {equity !== null && <span style={small}>equity {formatUsd(account?.ddEquity)}</span>}
          </div>
          <div className={`${CT_COL.status} flex flex-col items-center justify-center gap-1`}>
            <span
              style={{
                border: "1px solid",
                borderRadius: "4px",
                fontSize: "11px",
                padding: "2px 8px",
                color: isActive ? "var(--tv-up)" : "var(--tv-text-3)",
                borderColor: isActive ? "var(--tv-up)" : "var(--tv-text-3)",
              }}
            >
              {isActive ? "Running" : "Paused"}
            </span>
            {dd && <span style={{ ...small, color: dd.color }}>{dd.text}</span>}
          </div>
        </>
      ) : (
      <>
      <button
        className="w-1/4 cursor-pointer flex items-center gap-1 justify-between text-start"
        onClick={() => {
          handleExpand(index);
        }}
      >
        {(data.name)}
        <BsCaretDown size={20} />
      </button>
      <div className="w-1/6 text-center">
        {(brokerDetails.name)}
        <br />
        {brokerDetails.clientCode &&
          brokerDetails.clientCode !== "" &&
          `(${(brokerDetails.clientCode)})`}
      </div>
      <div className="tnum w-1/6 text-center">
        {data.activePositionsCount} | {data.totalPositionCount}
      </div>
      <div className="tnum w-1/6 text-center flex items-center justify-center gap-2">
        {data.multiplyer}x{" "}
        <span
          style={{
            border: "1px solid",
            borderRadius: "4px",
            fontSize: "11px",
            padding: "2px 8px",
            color: isActive ? "var(--tv-up)" : "var(--tv-text-3)",
            borderColor: isActive ? "var(--tv-up)" : "var(--tv-text-3)",
          }}
        >
          {isActive ? "Running" : "Paused"}
        </span>
      </div>
      </>
      )}
      <div className={`${copyTrade ? CT_COL.pnl : "w-1/12"} text-center`}>
        {totalPandL(data.totalProfitLoss)}
      </div>
      <div className={`${copyTrade ? CT_COL.actions : "w-1/12"} flex items-center justify-end`}>
        <Menubar className="bg-transparent border-none">
          <MenubarMenu>
            <MenubarTrigger className=" cursor-pointer">
              <IoIosMore size={20} />
            </MenubarTrigger>
            <MenubarContent>
              {data.isActive ? (
                <MenubarItem
                  onClick={() => {
                    handleStrategyMode({
                      strategyId: data.id,
                      status: false,
                    });
                  }}
                >
                  Pause Strategy
                </MenubarItem>
              ) : (
                <MenubarItem
                  onClick={() => {
                    handleStrategyMode({
                      strategyId: data.id,
                      status: true,
                    });
                  }}
                >
                  Resume Strategy
                </MenubarItem>
              )}
              <MenubarSeparator />
              {copyTrade ? (
                <>
                  <MenubarItem onClick={() => setPriceOpen(true)}>{sizeLabel}</MenubarItem>
                  <MenubarSeparator />
                  <MenubarItem onClick={() => setRiskOpen(true)}>Stop Loss &amp; Drawdown</MenubarItem>
                </>
              ) : (
              <MenubarSub>
                <MenubarSubTrigger>{sizeLabel}</MenubarSubTrigger>
                <MenubarSubContent>
                  {Array.from(Array(15).keys()).map((item) => {
                    return (
                      <MenubarItem
                        key={item}
                        onClick={() => {
                          handleMultiplierChange(String(item + 1));
                        }}
                      >
                        {item + 1}x
                      </MenubarItem>
                    );
                  })}
                </MenubarSubContent>
              </MenubarSub>
              )}
              <MenubarSeparator />
              {copyTrade ? (
                <MenubarItem onClick={() => onRemove?.()}>Remove</MenubarItem>
              ) : (
              <>
              <MenubarItem
                onClick={() => {
                  handleExitStrategy({
                    strategyId: data.id,
                    brokerId: brokerDetails.id,
                  });
                }}

              >

                Exit Strategy
              </MenubarItem>
              <MenubarSeparator />
              <MenubarItem
                onClick={() => {
                  handleDeleteStrategy({
                    strategyId: data.id,
                    brokerId: brokerDetails.id,
                  });
                }}
              >
                Delete Strategy
              </MenubarItem>
              <MenubarSeparator />
              <MenubarItem
                onClick={() => {
                  handleArchiveStrategy({ strategyId: data.id });
                }}
              >
                Archive Strategy
              </MenubarItem>
              </>
              )}
            </MenubarContent>
          </MenubarMenu>
        </Menubar>
      </div>
      {copyTrade && (
        <PriceDialog
          open={priceOpen}
          onOpenChange={setPriceOpen}
          userStrategyId={data.id}
          accountName={brokerDetails.name}
          currentLot={data.lotSize}
          onSaved={() => setStrategyChangeHappend(true)}
        />
      )}
      {copyTrade && (
        <RiskDialog
          open={riskOpen}
          onOpenChange={setRiskOpen}
          userStrategyId={data.id}
          accountName={brokerDetails.name}
          initial={riskFromRow(data, account ?? {})}
          equity={equity}
          onSaved={() => setStrategyChangeHappend(true)}
        />
      )}
    </div>
  );
};

export default StrategyTableRow;
