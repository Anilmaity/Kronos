"use client";
// React - Next default
import React, { useEffect } from "react";
import { useRouter } from "next/navigation";

// GraphQL
import { gql } from "@apollo/client";
import { client } from "@/GraphQL/client";

// icons
import { BiExit } from "react-icons/bi";

// hooks
import { useUserData } from "@/hooks/useUserData";

// lib
import { panelStyle } from "@/lib/tvStyles";

// componets
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
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

interface SuperAdminPagetableProps {
  clientCode: string;
  name: string;
  id: string;
  userbrokerpositions: {
    id: string;
    symbol: string;
    quantity: string;
    avgBuyPrice: string;
    profitLoss: string;
    ltp: string;
    token: string;
  }[];
  strategyPositions: {
    symbol: string;
    profitLoss: string;
    quantity: string;
    ltp: string;
    avgBuyPrice: string;
  }[];
}

const SuperAdminPage = () => {
  const router = useRouter();
  const { userData } = useUserData();

  const [tableData, setTableData] = React.useState<SuperAdminPagetableProps[]>(
    []
  );

  // check if the user is superuser or not
  useEffect(() => {
    // if (!localStorage.getItem("isSuperuser")) {
    //   router.push("/dashboard");
    // }
  }, [userData, router]);

  // fetch the data from the server and update the state
  useEffect(() => {
    const fetchData = async () => {
      const query = gql`
        query {
          allUserBrokers(includeDummy: true) {
            clientCode
            name
            id
            userbrokerpositions(activeOnly: true) {
              id
              symbol
              quantity
              avgBuyPrice
              profitLoss
              ltp
              token
            }
            strategyPositions {
              symbol
              profitLoss
              quantity
              ltp
              avgBuyPrice
            }
          }
        }
      `;

      const { data } = await client.query({ query, fetchPolicy: "no-cache" });

      setTableData(data.allUserBrokers);
    };

    fetchData();

    // limit the api call to only between 9:15 to 15:30 IST
    const now = new Date().toLocaleString("en-US", {
      timeZone: "Asia/Kolkata",
    });

    const currentDayOfWeek = new Date(now.split(", ")[0]).getDay();

    const currentHour = new Date(now).getHours();
    const currentMinute = new Date(now).getMinutes();

    // check that the current day is not a weekend
    if (currentDayOfWeek !== 0 && currentDayOfWeek !== 6) {
      // Check if the current time is within the desired time frame (9:12 to 15:33 IST)
      if (
        (currentHour === 9 && currentMinute >= 12) ||
        (currentHour > 9 && currentHour < 15) ||
        (currentHour === 15 && currentMinute <= 33)
      ) {
        const intervalId = setInterval(() => {
          fetchData().catch((error) => {
            console.error("Error fetching data:", error);
          });
        }, 1000);

        // Clean up the interval to prevent memory leaks
        return () => clearInterval(intervalId);
      }
    }
  }, []);

  return (
    <div className="h-full flex flex-col items-start w-full">
      <div className="flex flex-col">
        <span className="text-base font-semibold">Admin</span>
        <span className="text-sm" style={{ color: "var(--tv-text-soft)" }}>
          Per-broker positions — superadmin
        </span>
      </div>
      <div className="flex w-full flex-col items-start">
        {tableData.map((data, index) => {
          if (data.strategyPositions.length > 0) {
            return (
              <div
                className="w-full h-full max-w-full overflow-y-auto"
                key={data.id}
              >
                <div
                  className="mt-5 min-h-full w-full flex flex-col items-start justify-start px-2.5 lg:px-4 py-4 text-[10px] md:text-[12px] xl:text-sm min-w-[500px] md:min-w-[900px] lg:w-full gap-6"
                  style={panelStyle}
                >
                  <div className="text-base">
                    Broker Name: {(data.name)} (
                    {(data.clientCode)})
                  </div>
                  <div className="w-full flex flex-col gap-2">
                    <div className="my-2 text-sm font-semibold">
                      Algo Positions
                    </div>
                    <div className="flex items-center justify-normal w-full border-b py-1 md:py-2">
                      <div className="w-1/12 text-center">No.</div>
                      <div className="w-1/4">Symbol</div>
                      <div className="w-1/6 text-center">Quantity</div>
                      <div className="w-1/6 text-center">Avg Buy Price</div>
                      <div className="w-1/6 text-center">LTP</div>
                      <div className="w-2/12 text-center">Total P & L</div>
                    </div>
                    <div className="w-full">
                      {data.strategyPositions.map((strategy, index) => {
                        return (
                          <div
                            className="flex items-center justify-normal w-full border-b py-1 md:py-2"
                            key={index}
                          >
                            <div className="w-1/12 text-center">
                              {index + 1}
                            </div>
                            <div className="w-1/4">{strategy.symbol}</div>
                            <div className="w-1/6 text-center">
                              {strategy.quantity}
                            </div>
                            <div className="w-1/6 text-center">
                              {strategy.ltp}
                            </div>
                            <div className="w-1/6 text-center">
                              {strategy.avgBuyPrice}
                            </div>
                            <div
                              className="w-2/12 text-center"
                              style={{
                                color:
                                  parseFloat(strategy.profitLoss) < 0
                                    ? "var(--tv-down)"
                                    : "var(--tv-up)",
                              }}
                            >
                              {strategy.profitLoss}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  <div className="w-full flex flex-col gap-2">
                    <div className="my-2 text-sm font-semibold">
                      Actual Broker Positions
                    </div>
                    <div className="flex items-center justify-normal w-full border-b py-1 md:py-2">
                      <div className="w-1/12 text-center">No.</div>
                      <div className="w-1/4">Symbol</div>
                      <div className="w-1/6 text-center">Quantity</div>
                      <div className="w-1/6 text-center">Avg Buy Price</div>
                      <div className="w-1/6 text-center">LTP</div>
                      <div className="w-1/12 text-center">Total P & L</div>
                      <div className="w-1/12 text-end">Actions</div>
                    </div>
                    <div className="w-full">
                      {data.userbrokerpositions.map((position, index) => {
                        return (
                          <div
                            className="flex items-center justify-normal w-full border-b py-1 md:py-2"
                            key={position.id}
                          >
                            <div className="w-1/12 text-center">
                              {index + 1}
                            </div>
                            <div className="w-1/4">{position.symbol}</div>
                            <div className="w-1/6 text-center">
                              {position.quantity}
                            </div>
                            <div className="w-1/6 text-center">
                              {position.avgBuyPrice}
                            </div>
                            <div className="w-1/6 text-center">
                              {position.ltp}
                            </div>
                            <div
                              className="w-2/12 text-center"
                              style={{
                                color:
                                  parseFloat(position.profitLoss) < 0
                                    ? "var(--tv-down)"
                                    : "var(--tv-up)",
                              }}
                            >
                              {position.profitLoss}
                            </div>
                            <div className="w-1/12 text-end">
                              <AlertDialog>
                                <TooltipProvider>
                                  <Tooltip>
                                    <AlertDialogTrigger asChild>
                                      <TooltipTrigger>
                                        <BiExit className={`w-5 h-5`} />
                                      </TooltipTrigger>
                                    </AlertDialogTrigger>
                                    <TooltipContent>
                                      <p>Exit {position.symbol}</p>
                                    </TooltipContent>
                                  </Tooltip>
                                </TooltipProvider>
                                <AlertDialogContent>
                                  <AlertDialogHeader>
                                    <AlertDialogTitle>
                                      Do you want to Exit?
                                    </AlertDialogTitle>
                                    <AlertDialogDescription>
                                      This action cannot be undone. This will
                                      exit all the position from the strategy.
                                    </AlertDialogDescription>
                                  </AlertDialogHeader>
                                  <AlertDialogFooter>
                                    <AlertDialogCancel>
                                      Cancel
                                    </AlertDialogCancel>
                                    <AlertDialogAction
                                      className="bg-[var(--tv-down)] text-white hover:bg-[var(--tv-down)]"
                                      // onClick={() => {
                                      //   exitPosition({
                                      //     symbol: position.symbol,
                                      //     quantity: position.quantity,
                                      //     userbrokerId: data.id,
                                      //     token: position.token,
                                      //     buy_or_sell:
                                      //       parseInt(position.quantity) > 0
                                      //         ? "SELL"
                                      //         : "BUY",
                                      //   });
                                      // }}
                                    >
                                      Exit
                                    </AlertDialogAction>
                                  </AlertDialogFooter>
                                </AlertDialogContent>
                              </AlertDialog>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
              </div>
            );
          } else {
            return null;
          }
        })}
      </div>
    </div>
  );
};

export default SuperAdminPage;
