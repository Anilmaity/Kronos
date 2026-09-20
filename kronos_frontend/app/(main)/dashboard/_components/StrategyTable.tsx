/* eslint-disable react-hooks/exhaustive-deps */
// React - Next default
import React, { useEffect, useState } from "react";

// Hooks
import { useExpandIndex } from "@/hooks/strategy/useExpandIndex";
import { useStrategyChangeHappend } from "@/hooks/useStrategyChangeHappend";
import { middleware } from "@/GraphQL/middleware";

// Utils
import { getCurrencySymbol } from "@/utils/currencySymbol";

// Types
import { UserExchangeSetProps } from "@/types";

// Components
import StrategyBox from "./StrategyBox";
import StrategyTableRow from "./StrategyTableRow";
import { dateFormatter } from "@/utils/dateFormatter";
import { gql } from "@apollo/client";
import { client } from "@/GraphQL/client";

interface StrategyTableProps {
  selectedDate: Date;
  brokerIds: string[];
}

const StrategyTable: React.FC<StrategyTableProps> = ({
  selectedDate,
  brokerIds,
}) => {
  let global_index = 0;
  const { expandIndex, setExpandIndex } = useExpandIndex();

  const { setStrategyChangeHappend, strategyChangeHappend } =
    useStrategyChangeHappend();

  const [tableData, setTableData] = React.useState<UserExchangeSetProps[]>([]);

  const [totalProfitLoss, setTotalProfitLoss] = useState<number>(0);

  const [userStrategyIds, setUserStrategyIds] = useState<string[]>([]);

  const currencySymbol = getCurrencySymbol();

  const fetchData = async () => {
    const query = gql`
  query GetUserData($userstrategyIds: [UUID!]!, $date: Date!) {
  getuserdata {
    userbrokers {
      id
      isActive
      name
      label
      accountHolderName
      marginAvailable

      userstrategys {
        id
        name
        isActive
        multiplyer
        createdAt
        activePositionsCount(date: $date)
        totalPositionCount(date: $date)
        totalProfitLoss(date: $date)
        strategy {
          id
          isActive
          capitalRequired
          __typename
        }
        positions(userstrategyIds: $userstrategyIds, date: $date) {
          id
          symbol
          quantity
          profitLoss
          avgBuyPrice
          totalValue
          ltp
          triggers {
            id
            createdAt
            modifiedAt
            triggerType
            triggerPrice
            side
            status
            quantity
            __typename
          }
          Orders {
            id
            createdAt
            symbol
            price
            condition
            quantity
            orderType
            status
            reason
            __typename
          }
          
        }
        
      }
    }
  }
}
    `;
    try {
      const selectDate =
        `${selectedDate.getFullYear()}-` +
        `${String(selectedDate.getMonth() + 1).padStart(2, "0")}-` +
        `${String(selectedDate.getDate()).padStart(2, "0")}`;
      const { data } = await client.query({
        query,
        variables: {
          brokerIds,
          userstrategyIds: userStrategyIds,
          date: selectDate,
        },
        fetchPolicy: "no-cache",
      });

      const userbrokers = data.getuserdata?.userbrokers ?? [];
      setTableData(userbrokers);

      const sum = userbrokers.reduce(
        (acc: number, broker: UserExchangeSetProps) =>
          acc +
          broker.userstrategys.reduce(
            (sAcc: number, strategy) => sAcc + Number(strategy.totalProfitLoss ?? 0),
            0
          ),
        0
      );
      setTotalProfitLoss(sum);
    } catch (err) {
      middleware(err);
    }
  }; // Fetch Data

  const handleUserStrategyExpand = (strategyId: string) => {
    if (userStrategyIds.includes(strategyId)) {
      const newUserStrategyIds = userStrategyIds.filter(
        (id) => id !== strategyId
      );
      setUserStrategyIds(newUserStrategyIds);
    } else {
      setUserStrategyIds([...userStrategyIds, strategyId]);
    }
  };

  useEffect(() => {
    fetchData();

    const intervalId = setInterval(() => {
      fetchData().catch((error) => {
        console.error("Error fetching data:", error);
      });
    }, 15000);

    // Clean up the interval to prevent memory leaks
    return () => clearInterval(intervalId);

  }, [brokerIds, userStrategyIds, selectedDate]);

  useEffect(() => {
    // Fetch data when strategyChangeHappend
    if (strategyChangeHappend) {
      fetchData();
      setStrategyChangeHappend(false);
    }
  }, [strategyChangeHappend]);

  const handleExpand = (index: number, strategy: string) => {
    if (expandIndex.includes(index)) {
      setExpandIndex(expandIndex.filter((i) => i !== index));
    } else {
      setExpandIndex([...expandIndex, index]);
    }
    handleUserStrategyExpand(strategy);
  };

  useEffect(() => {
    const handleRouteChange = () => {
      // window.location.reload();
      setExpandIndex([]);
    };

    handleRouteChange();
  }, []);

  if (tableData.length > 0) {
    return (
      <div
        className="w-full flex flex-col items-start justify-start overflow-x-auto"
        style={{
          background: "var(--tv-surface)",
          border: "1px solid var(--tv-border)",
          borderRadius: "6px",
        }}
      >
        {/* Table header */}
        <div
          className="flex items-center w-full px-4 py-3 min-w-[860px]"
          style={{
            borderBottom: "1px solid var(--tv-border)",
            fontSize: "11px",
            letterSpacing: "0.4px",
            textTransform: "uppercase",
            color: "var(--tv-text-3)",
            fontWeight: 500,
          }}
        >
          <div className="w-1/12 text-center">No.</div>
          <div className="w-1/4">Strategy</div>
          <div className="w-1/6 text-center">Execution</div>
          <div className="w-1/6 text-center">Open · Total</div>
          <div className="w-1/6 text-center">Multiplier · Status</div>
          <div className="w-1/12 text-center">P &amp; L</div>
          <div className="w-1/12 text-end">Actions</div>
        </div>

        {tableData.map((exchange) => {
          return (
            <div key={exchange.id} className="w-full min-w-[860px]">
              {exchange.userstrategys.map((strategy, sindex) => {
                const currentIndex = global_index++;
                if (expandIndex.includes(currentIndex)) {
                  return (
                    <div key={strategy.id} className="w-full">
                      <StrategyBox
                        data={strategy}
                        handleExpand={() =>
                          handleExpand(currentIndex, strategy.id)
                        }
                        index={currentIndex}
                        brokerDetails={{
                          id: exchange.id,
                          name: exchange.label || exchange.name,
                          clientCode: "",
                          marginAvailable: exchange.marginAvailable,
                          accountHolderName: exchange.accountHolderName,
                        }}
                      />
                    </div>
                  );
                } else {
                  return (
                    <div key={strategy.id} className="w-full">
                      <StrategyTableRow
                        data={strategy}
                        handleExpand={() =>
                          handleExpand(currentIndex, strategy.id)
                        }
                        index={currentIndex}
                        brokerDetails={{
                          id: exchange.id,
                          name: exchange.label || exchange.name,
                          clientCode: "",
                          marginAvailable: exchange.marginAvailable,
                          accountHolderName: exchange.accountHolderName,
                        }}
                      />
                    </div>
                  );
                }
              })}
            </div>
          );
        })}
        <div
          className="flex items-center justify-end gap-6 w-full min-w-[860px] py-3 px-4"
          style={{
            borderTop: "1px solid var(--tv-border)",
            fontSize: "11px",
            letterSpacing: "0.4px",
            textTransform: "uppercase",
            fontWeight: 600,
          }}
        >
          <div style={{ color: "var(--tv-text-3)" }}>
            Total P&amp;L ·{" "}
            {dateFormatter(selectedDate.toISOString().split("T")[0])}
          </div>
          <div
            className="tnum"
            style={{
              color: totalProfitLoss < 0 ? "var(--tv-down)" : "var(--tv-up)",
              minWidth: "120px",
              textAlign: "right",
            }}
          >
            {currencySymbol}
            {totalProfitLoss.toFixed(2)}
          </div>
        </div>
      </div>
    );
  } else {
    return (
      <div
        className="w-full flex items-center justify-center px-4 py-16"
        style={{
          background: "var(--tv-surface)",
          border: "1px solid var(--tv-border)",
          borderRadius: "6px",
          fontSize: "13px",
          color: "var(--tv-text-3)",
        }}
      >
        No data available for selected date
      </div>
    );
  }
};

export default StrategyTable;
