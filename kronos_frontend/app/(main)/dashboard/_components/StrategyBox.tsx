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
} from "@/GraphQL/strategyControls";

// Icons
import { VscDebugStart } from "react-icons/vsc";
import { BiExit } from "react-icons/bi";
import { RiDeleteBin6Line } from "react-icons/ri";
import { PiArrowsIn } from "react-icons/pi";
import { BsStopCircle } from "react-icons/bs";

// Utils
import { dateFormatter } from "@/utils/dateFormatter";
import { formatCapital } from "@/utils/FormatCapital";
import { getCurrencySymbol } from "@/utils/currencySymbol";

// Types
import { UserStrategysProps } from "@/types";
import { useStrategyChangeHappend } from "@/hooks/useStrategyChangeHappend";

// Components
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

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
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";

import PositionRows from "./PositionRows";
import { middleware } from "@/GraphQL/middleware";

interface StrategyBoxProps {
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

const StrategyBox: React.FC<StrategyBoxProps> = ({
  index,
  handleExpand,
  data,
  brokerDetails,
}) => {
  const [isActive, setIsActive] = useState<boolean>(data.isActive);
  const { setStrategyChangeHappend } = useStrategyChangeHappend();

  const currencySymbol = getCurrencySymbol();

  const totalPandL = (totalPandL: number) => {
    const totalPandLClass = totalPandL < 0 ? "text-down" : "text-up";

    return (
      <div
        className="font-bold w-full flex items-center text-[12px] md:text-[14px] xl:text-base justify-end gap-4"
      >
        <div style={{ color: "var(--tv-text-3)" }}>Total P&L:</div>
        <div className={`tnum ${totalPandLClass} mr-24`}>
          {totalPandL.toFixed(2)}
        </div>
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

  const handleExitStrategy = async ({
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

  const handleDeleteStrategy = ({
    strategyId,
    brokerId,
  }: {
    strategyId: string;
    brokerId: string;
  }) => {
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

  return (
    <div className="w-full flex py-2 border-b">
      <div className="w-1/12 text-center mt-3 font-semibold">{index + 1}</div>
      <div className="flex flex-col items-start justify-start w-11/12 mb-3 pr-3">
        <div
          className="flex items-center justify-between w-full border-b pb-4"
          style={{ borderColor: "var(--tv-border)" }}
        >
          <button
            className="cursor-pointer font-semibold"
            onClick={() => handleExpand(index)}
          >
            {(data.name)}
          </button>
          <div className="flex items-center gap-6">
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger
                  onClick={() => {
                    handleExpand(index);
                  }}
                  className="py-1 lg:py-2 h-8 lg:h-12 w-8 lg:w-12 text-xl lg:text-4xl rounded-full flex items-center justify-center"
                  style={{ background: "var(--tv-surface-2)", color: "var(--tv-text-2)" }}
                >
                  <PiArrowsIn />
                </TooltipTrigger>
                <TooltipContent>
                  <p>Collapse Box</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
            <div
              className="py-1 lg:py-2 h-8 lg:h-12 w-8 lg:w-12 text-xl lg:text-2xl rounded-full flex items-center justify-center text-white"
              style={{ background: "var(--tv-accent)" }}
            >
              {isActive ? (
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger
                      onClick={() => {
                        setIsActive(false);
                        handleStrategyMode({
                          strategyId: data.id,
                          status: false,
                        });
                      }}
                    >
                      <BsStopCircle />
                    </TooltipTrigger>
                    <TooltipContent>
                      <p>Pause Strategy</p>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              ) : (
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger
                      onClick={() => {
                        setIsActive(true);
                        handleStrategyMode({
                          strategyId: data.id,
                          status: true,
                        });
                      }}
                    >
                      <VscDebugStart />
                    </TooltipTrigger>
                    <TooltipContent>
                      <p>Start Strategy</p>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              )}
            </div>
            <div
              className="py-1 lg:py-2 h-8 lg:h-12 w-8 lg:w-12 text-xl lg:text-2xl rounded-full flex items-center justify-center text-white"
              style={{ background: "var(--tv-accent)" }}
            >
              <AlertDialog>
                <TooltipProvider>
                  <Tooltip>
                    <AlertDialogTrigger asChild>
                      <TooltipTrigger>
                        <BiExit />
                      </TooltipTrigger>
                    </AlertDialogTrigger>
                    <TooltipContent>
                      <p>Exit Strategy</p>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
                <AlertDialogContent>
                  <AlertDialogHeader>
                    <AlertDialogTitle>Do you want to Exit?</AlertDialogTitle>
                    <AlertDialogDescription>
                      This action cannot be undone. This will exit all the
                      position from the strategy.
                    </AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter>
                    <AlertDialogCancel>Cancel</AlertDialogCancel>
                    <AlertDialogAction
                      className="text-white"
                      style={{ background: "var(--tv-accent)", borderRadius: "6px" }}
                      onClick={() => {
                        handleExitStrategy({
                          strategyId: data.id,
                          brokerId: brokerDetails.id,
                        });
                      }}
                    >
                      Exit
                    </AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
            </div>
            <div
              className="py-1 lg:py-2 h-8 lg:h-12 w-8 lg:w-12 text-xl lg:text-2xl rounded-full flex items-center justify-center text-white"
              style={{ background: "var(--tv-down)" }}
            >
              <AlertDialog>
                <TooltipProvider>
                  <Tooltip>
                    <AlertDialogTrigger asChild>
                      <TooltipTrigger>
                        <RiDeleteBin6Line />
                      </TooltipTrigger>
                    </AlertDialogTrigger>
                    <TooltipContent>
                      <p>Delete Strategy</p>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
                <AlertDialogContent>
                  <AlertDialogHeader>
                    <AlertDialogTitle>Do you want to Delete?</AlertDialogTitle>
                    <AlertDialogDescription>
                      This action cannot be undone. This will exit all the
                      position from the strategy if active and will remove all
                      the previos and this data from database and unsubscribe
                      this strategy.
                    </AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter>
                    <AlertDialogCancel>Cancel</AlertDialogCancel>
                    <AlertDialogAction
                      className="text-white"
                      style={{ background: "var(--tv-down)", borderRadius: "6px" }}
                      onClick={() => {
                        handleDeleteStrategy({
                          strategyId: data.id,
                          brokerId: brokerDetails.id,
                        });
                      }}
                    >
                      Delete
                    </AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
            </div>
          </div>
        </div>
        <div className="table w-full py-4 border-b" style={{ borderColor: "var(--tv-border)" }}>
          <div className="flex items-center w-full">
            <div className="flex items-center gap-4 w-1/2">
              <div className="font-semibold">Deployed On :</div>
              <div>{dateFormatter(data.createdAt)}</div>
            </div>
            <div className="flex items-center gap-4 w-1/2">
              <div className="font-semibold">Required Capital :</div>
              <div>
                {formatCapital(
                  parseInt((data.strategy.capitalRequired)) *
                    parseInt(data.multiplyer)
                )}
              </div>
            </div>
          </div>
          <div className="flex items-center w-full mt-4">
            <div className="flex items-center gap-4 w-1/2">
              <div className="font-semibold">Broker :</div>
              <div>
                {(brokerDetails.name)}
                {brokerDetails.clientCode &&
                  brokerDetails.clientCode !== "" &&
                  `(${(brokerDetails.clientCode)})`}
              </div>
            </div>
            <div className="flex items-center gap-4 w-1/2">
              <div className="font-semibold">Account Holder Name :</div>
              <div>{(brokerDetails.accountHolderName)}</div>
            </div>
          </div>
          <div className="flex items-center w-full mt-4">
            <div className="flex items-center gap-4 w-1/2">
              <div className="font-semibold">Available Capital :</div>
              <div>
                {formatCapital(
                  parseFloat((brokerDetails.marginAvailable))
                )}
              </div>
            </div>
            <div className="flex items-center gap-4 w-1/2">
              <div className="font-semibold">Multiplier :</div>
              <Select onValueChange={(event) => handleMultiplierChange(event)}>
                <SelectTrigger
                  className="w-[125px] p-2 lg:p-4 h-7 lg:h-10"
                  defaultValue={data.multiplyer}
                >
                  <SelectValue placeholder={data.multiplyer} />
                </SelectTrigger>
                <SelectContent className="max-w-[5rem]">
                  {[...Array(7)].map((_, index) => (
                    <SelectItem
                      key={index + 1}
                      value={(index + 1).toString()}
                      defaultChecked={(index + 1).toString() === data.multiplyer}
                    >
                      {index + 1}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </div>
        {data.positions.length > 0 ? (
          <div className="w-full">
            <div className="table w-full py-4">
              <div
                className="flex items-center w-full p-2"
                style={{
                  borderBottom: "1px solid var(--tv-border)",
                  fontSize: "11px",
                  fontWeight: 500,
                  letterSpacing: "0.4px",
                  textTransform: "uppercase",
                  color: "var(--tv-text-3)",
                }}
              >
                <div className="flex items-center gap-4 w-1/4">
                  Instrument symbol
                </div>
                <div className="flex items-center gap-4 w-1/12">Qty</div>
                <div className="flex items-center gap-4 w-1/6">
                  LTP ({currencySymbol})
                </div>
                <div className="flex items-center gap-4 w-1/6">
                  Buy Price ({currencySymbol})
                </div>
                <div className="flex items-center gap-4 w-1/6">
                  Val ({currencySymbol})
                </div>
                <div className="flex items-center gap-4 w-1/6">
                  P & L ({currencySymbol})
                </div>
              </div>
              {data.positions.map((pos) => {
                return <PositionRows pos={pos} key={pos.id} />;
              })}
            </div>
            <div>{totalPandL(data.totalProfitLoss)}</div>
          </div>
        ) : (
          <div className="flex items-center w-full justify-center py-4 h-20">
            No Positions Available
          </div>
        )}
      </div>
    </div>
  );
};

export default StrategyBox;
