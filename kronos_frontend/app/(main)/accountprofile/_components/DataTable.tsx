/* eslint-disable react-hooks/exhaustive-deps */
// Icons
import { MoreHorizontal } from "lucide-react";

// Hooks
import { useRiskProfiles } from "@/hooks/useRiskProfiles";

//GraphQl
import { gql } from "@apollo/client";
import { client } from "@/GraphQL/client";

//Icons
import { LuChevronsUp, LuChevronsDown } from "react-icons/lu";

// Components
import { ControllerColumn } from "./main";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuPortal,
  DropdownMenuSeparator,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

type TsortedBy =
  | "name"
  | "monthly"
  | "weekly"
  | "daily"
  | "status"
  | "profile"
  | "broker";

type TsortOrder = "increase" | "decrease";

interface DataTableProps {
  data: ControllerColumn[];
  currentPage: number;
  setChangedRiskProfile: (value: boolean) => void;
  setSortedBy: (value: TsortedBy) => void;
  setSortOrder: (value: TsortOrder) => void;
  sortOrder: TsortOrder;
  sortedBy: TsortedBy;
  maxPageSize: number;
}

const DataTable: React.FC<DataTableProps> = ({
  data,
  currentPage,
  setChangedRiskProfile,
  setSortedBy,
  setSortOrder,
  sortOrder,
  sortedBy,
  maxPageSize,
}) => {
  const { riskProfiles } = useRiskProfiles();

  // reseting the risk profile list
  const handleSortOrderChange = () => {
    setSortOrder(sortOrder === "increase" ? "decrease" : "increase");
  };

  // Function to handle sorting by a particular field
  const handleSortBy = (field: TsortedBy) => {
    setSortedBy(field);
    if (sortedBy === field) {
      handleSortOrderChange();
    }
  };

  // change user risk profile
  const changeRiskProfile = async (id: string, riskProfileId: string) => {
    const mutation = gql`
        mutation{
          ChangeRiskProfile(
            riskProfileId:"${riskProfileId}"
            userbrokerId:"${id}"
          ){
            Response
          }
      }
    `;

    client
      .mutate({
        mutation: mutation,
      })
      .then((response) => {
        toast.success("Risk Profile Changed Successfully");
        setChangedRiskProfile(true);
      })
      .catch((error) => {
        toast.error("Error Changing Risk Profile");
      });
  };

  return (
    <div className="w-full overflow-auto pb-4 max-w-full">
      <div
        className="min-h-full w-full flex flex-col items-start justify-start px-2.5 lg:px-4 py-4 text-[10px] md:text-[12px]  min-w-[900px] lg:w-full"
        style={{
          background: "var(--tv-surface)",
          border: "1px solid var(--tv-border)",
          borderRadius: "8px",
        }}
      >
        <div
          className="flex items-center justify-normal w-full border-b py-1 md:py-2 font-semibold uppercase tracking-wider"
          style={{ color: "var(--tv-text-soft)" }}
        >
          <div className="w-1/12 text-center">Id</div>
          <button
            className="w-3/12 flex items-center justify-between px-2 cursor-pointer"
            onClick={() => handleSortBy("name")}
          >
            Name
            {sortedBy === "name" &&
              (sortOrder === "increase" ? (
                <LuChevronsDown />
              ) : (
                <LuChevronsUp />
              ))}
          </button>
          <button
            className="w-1/12 flex items-center justify-between px-2 cursor-pointer"
            onClick={() => handleSortBy("broker")}
          >
            <div className="w-[70%]">Broker</div>
            {sortedBy === "broker" &&
              (sortOrder === "increase" ? (
                <LuChevronsDown />
              ) : (
                <LuChevronsUp />
              ))}
          </button>
          <div className="w-1/12 text-center">Client Code</div>
          <button
            className="w-1/12 flex items-center justify-between px-2 cursor-pointer"
            onClick={() => handleSortBy("daily")}
          >
            <div className="w-[70%]">Daily PnL %</div>
            {sortedBy === "daily" &&
              (sortOrder === "increase" ? (
                <LuChevronsDown />
              ) : (
                <LuChevronsUp />
              ))}
          </button>
          <button
            className="w-1/12 flex items-center justify-between px-2 cursor-pointer"
            onClick={() => handleSortBy("weekly")}
          >
            <div className="w-[70%]">Weekly PnL % </div>
            {sortedBy === "weekly" &&
              (sortOrder === "increase" ? (
                <LuChevronsDown />
              ) : (
                <LuChevronsUp />
              ))}
          </button>
          <button
            className="w-1/12 flex items-center justify-between px-2 cursor-pointer"
            onClick={() => handleSortBy("monthly")}
          >
            <div className="w-[70%]">Monthly PnL % </div>
            {sortedBy === "monthly" &&
              (sortOrder === "increase" ? (
                <LuChevronsDown />
              ) : (
                <LuChevronsUp />
              ))}
          </button>
          <button
            className="w-1/12 flex items-center justify-between px-2 cursor-pointer"
            onClick={() => handleSortBy("status")}
          >
            <div className="w-[70%]">Status </div>
            {sortedBy === "status" &&
              (sortOrder === "increase" ? (
                <LuChevronsDown />
              ) : (
                <LuChevronsUp />
              ))}
          </button>
          <button
            className="w-1/12 flex items-center justify-between px-2 cursor-pointer"
            onClick={() => handleSortBy("profile")}
          >
            <div className="w-[70%]">Profile </div>
            {sortedBy === "profile" &&
              (sortOrder === "increase" ? (
                <LuChevronsDown />
              ) : (
                <LuChevronsUp />
              ))}
          </button>
          <div className="w-1/12 text-center">Actions</div>
        </div>
        {data.map((item: ControllerColumn, index) => {
          const decryptedStatus: string = (item.status);
          let statusStyle: React.CSSProperties;

          if (
            decryptedStatus !== "Currently active" &&
            decryptedStatus !== "Currently Active"
          ) {
            statusStyle = decryptedStatus.includes("-")
              ? { color: "var(--tv-down)" }
              : { color: "var(--tv-up)" };
          } else {
            statusStyle = {};
          }

          return (
            <div
              key={item.id}
              className="flex items-center justify-normal w-full border-b py-1 md:py-2 font-semibold"
            >
              <div className="w-1/12 text-center">
                {index + 1 + maxPageSize * (currentPage - 1)}
              </div>
              <div className="w-3/12">
                {(item.accountHolderName)}
              </div>
              <div className="w-1/12 text-center">{(item.name)}</div>
              <div className="w-1/12 text-center">
                {(item.clientCode)}
              </div>
              <div
                className="w-1/12 text-center font-semibold"
                style={{
                  color:
                    parseFloat((item.dailyPnlPercentage)) < 0
                      ? "var(--tv-down)"
                      : "var(--tv-up)",
                }}
              >
                {(item.dailyPnlPercentage)}
              </div>
              <div
                className="w-1/12 text-center font-semibold"
                style={{
                  color:
                    parseFloat((item.weeklyPnlPercentage)) < 0
                      ? "var(--tv-down)"
                      : "var(--tv-up)",
                }}
              >
                {(item.weeklyPnlPercentage)}
              </div>
              <div
                className="w-1/12 text-center font-semibold"
                style={{
                  color:
                    parseFloat((item.monthlyPnlPercentage)) < 0
                      ? "var(--tv-down)"
                      : "var(--tv-up)",
                }}
              >
                {(item.monthlyPnlPercentage)}
              </div>
              <div
                className="w-1/12 text-center font-semibold"
                style={statusStyle}
              >
                {decryptedStatus}
              </div>
              <div className="w-1/12 text-center">{item.riskprofilename}</div>
              <div className="w-1/12 text-center">
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="ghost" className="h-8 w-8 p-0">
                      <span className="sr-only">Open menu</span>
                      <MoreHorizontal className="h-4 w-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuLabel>Actions</DropdownMenuLabel>
                    <DropdownMenuItem
                      onClick={() => navigator.clipboard.writeText(item.id)}
                    >
                      Copy user ID
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuGroup>
                      <DropdownMenuSub>
                        <DropdownMenuSubTrigger>
                          Risk Management Level
                        </DropdownMenuSubTrigger>
                        <DropdownMenuPortal>
                          <DropdownMenuSubContent>
                            {riskProfiles.map((riskProfile) => (
                              <DropdownMenuItem
                                key={riskProfile.id}
                                onClick={() => {
                                  changeRiskProfile(item.id, riskProfile.id);
                                }}
                              >
                                {riskProfile.name}
                              </DropdownMenuItem>
                            ))}
                          </DropdownMenuSubContent>
                        </DropdownMenuPortal>
                      </DropdownMenuSub>
                    </DropdownMenuGroup>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default DataTable;
