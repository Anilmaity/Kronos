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
import { UserStrategysProps } from "@/types";

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
}

const StrategyTableRow: React.FC<StrategyTableRowProps> = ({
  index,
  handleExpand,
  data,
  brokerDetails,
}) => {
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
          toast.success("Multiplier Changed Successfully");
          setStrategyChangeHappend(true);
        } else {
          toast.error("Something went wrong in changing multiplier");
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
      <div className="tnum w-1/12 text-center">{index + 1}</div>
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
      <div className="w-1/12 text-center">
        {totalPandL(data.totalProfitLoss)}
      </div>
      <div className="w-1/12 flex items-center justify-end">
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
              <MenubarSub>
                <MenubarSubTrigger>Multiplier</MenubarSubTrigger>
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
              <MenubarSeparator />
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
            </MenubarContent>
          </MenubarMenu>
        </Menubar>
      </div>
    </div>
  );
};

export default StrategyTableRow;
