/* eslint-disable react-hooks/exhaustive-deps */
// React - Next default
import React, { useEffect } from "react";

// GraphQL
import { gql } from "@apollo/client";
import { client } from "@/GraphQL/client";

// utils
import { getCurrencySymbol } from "@/utils/currencySymbol";

// Types
import { UserExchangeSetProps } from "@/types";
import { middleware } from "@/GraphQL/middleware";

const UserBrokerPositionTable = ({
  selectedDate,
  brokerIds,
}: {
  selectedDate: Date;
  brokerIds: string[];
}) => {
  const [tableData, setTableData] = React.useState<UserExchangeSetProps[]>([]);

  const currencySymbol = getCurrencySymbol();

  const fetchData = async () => {
    const query = gql`
      query GetUserData($date: Date!, $brokerIds: [UUID!]!) {
        getuserdata {
          userexchanges(brokers: $brokerIds) {
            id
            name
            isActive
            marginUsed
            accountHolderName
            userbrokerpositions(date: $date) {
              id
              symbol
              quantity
              avgBuyPrice
              profitLoss
              ltp
            }
          }
        }
      }
    `;

    try {
      const selectDate = selectedDate.toISOString().split("T")[0];
      const { data } = await client.query({
        query: query,
        variables: {
          date: selectDate,
          brokerIds,
        },
        fetchPolicy: "no-cache",
      });
      setTableData(data.getuserdata.userexchanges);
    } catch (err: any) {
      middleware(err);
    }
  };

  useEffect(() => {
    fetchData();

    const intervalId = setInterval(() => {
      fetchData().catch((error) => {
        console.error("Error fetching data:", error);
      });
    }, 4000);

    // Clean up the interval to prevent memory leaks
    return () => clearInterval(intervalId);


  }, [selectedDate, brokerIds]);

  if (tableData.length > 0) {
    return (
      <div className="flex flex-col gap-4">
        {tableData.map((exchange) => {
          if (exchange.userbrokerpositions.length > 0) {
            let grandTotalPandL: number = 0;
            exchange.userbrokerpositions.map((position) => {
              grandTotalPandL = grandTotalPandL + Number(position.profitLoss);
            });
            return (
              <div
                key={exchange.id}
                className="min-h-full w-full flex flex-col items-start justify-start px-2.5 lg:px-4 py-4 text-[10px] md:text-[12px] xl:text-sm min-w-[500px] lg:w-full"
                style={{
                  background: "var(--tv-surface)",
                  border: "1px solid var(--tv-border)",
                  borderRadius: "8px",
                }}
              >
                <div
                  className="flex items-center justify-normal w-full py-1 md:py-2 font-semibold text-lg"
                  style={{ borderBottom: "1px solid var(--tv-border)" }}
                >
                  Positions Of {exchange.name}
                </div>
                <div className="flex flex-col w-full px-3">
                  <div
                    className="flex items-center justify-normal w-full py-1 md:py-2"
                    style={{
                      borderBottom: "1px solid var(--tv-border)",
                      fontSize: "11px",
                      fontWeight: 500,
                      letterSpacing: "0.4px",
                      textTransform: "uppercase",
                      color: "var(--tv-text-3)",
                    }}
                  >
                    <div className="w-1/12">No. </div>
                    <div className="w-1/3">Instrument Symbol</div>
                    <div className="w-1/12 text-center">Qty</div>
                    <div className="w-1/6 text-center">Avg. Price.</div>
                    <div className="w-1/6 text-center">LTP</div>
                    <div className="w-1/6 text-center">P&L</div>
                    {/* <div className="w-1/12"></div> */}
                  </div>
                  <div className="flex flex-col w-full items-center gap-2">
                    {exchange.userbrokerpositions.map((position, pindex) => {
                      return (
                        <div
                          key={position.id}
                          className="flex items-center justify-normal w-full py-1 md:py-2 hover:bg-[var(--tv-surface-2)]"
                          style={{ borderBottom: "1px solid var(--tv-border)", minHeight: "36px" }}
                        >
                          <div className="tnum w-1/12">{pindex + 1}</div>
                          <div className="w-1/3">{position.symbol}</div>
                          <div className="tnum w-1/12 text-center">
                            {position.quantity}
                          </div>
                          <div className="tnum w-1/6 text-center">
                            {position.avgBuyPrice}
                          </div>
                          <div className="tnum w-1/6 text-center">
                            {position.ltp}
                          </div>
                          <div
                            className={`tnum w-1/6 text-center font-semibold ${
                              Number(position.profitLoss) < 0
                                ? "text-down"
                                : "text-up"
                            }`}
                          >
                            {Number(position.profitLoss).toFixed(2)}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                  <div
                    className={`tnum flex items-center justify-center gap-6 w-full py-2 font-semibold ${
                      grandTotalPandL < 0 ? "text-down" : "text-up"
                    }`}
                    style={{ borderBottom: "1px solid var(--tv-border)" }}
                  >
                    <div>
                      Total Profit and Loss of (
                      {`${selectedDate.getFullYear()}-${String(
                        selectedDate.getMonth() + 1
                      ).padStart(2, "0")}-${String(
                        selectedDate.getDate()
                      ).padStart(2, "0")}`}
                      )
                    </div>
                    <div>
                      {currencySymbol + " "}
                      {grandTotalPandL.toFixed(2)}
                    </div>
                  </div>
                </div>
              </div>
            );
          } else {
            return (
              <div
                key={exchange.id}
                className="min-h-full w-full flex items-center justify-center px-4 py-4 text-sm"
                style={{
                  background: "var(--tv-surface)",
                  border: "1px solid var(--tv-border)",
                  borderRadius: "8px",
                  color: "var(--tv-text-3)",
                }}
              >
                No Positions Available for {exchange.name}
              </div>
            );
          }
        })}
      </div>
    );
  } else {
    return (
      <div
        className="min-h-full w-full flex items-center justify-center px-4 py-4 text-sm"
        style={{
          background: "var(--tv-surface)",
          border: "1px solid var(--tv-border)",
          borderRadius: "8px",
          color: "var(--tv-text-3)",
        }}
      >
        No Data Available for Selected Broker
      </div>
    );
  }
};

export default UserBrokerPositionTable;
