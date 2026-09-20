/* eslint-disable react-hooks/exhaustive-deps */
// React - Next Default
"use client";
import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

// GraphQL
import { gql } from "@apollo/client";
import { client } from "@/GraphQL/client";

// Hooks
import { useRiskProfiles } from "@/hooks/useRiskProfiles";
import { useUserData } from "@/hooks/useUserData";

// Components
import DataTable from "./DataTable";
import RiskProfileTable from "./RiskProfileTable";
import { Button } from "@/components/ui/button";

import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export interface RiskProfileTableData {
  id: string;
  name: string;
  dailyLossLimitPercentage: string;
  dailyProfitLimitPercentage: string;
  weeklyLossLimitPercentage: string;
  weeklyProfitLimitPercentage: string;
  monthlyLossLimitPercentage: string;
  monthlyProfitLimitPercentage: string;
}

export interface ControllerColumn {
  id: string;
  name: string;
  clientCode: string;
  accountHolderName: string;
  monthlyPnlPercentage: string;
  weeklyPnlPercentage: string;
  dailyPnlPercentage: string;
  status: string;
  riskprofilename: string;
  [key: string]: string; // Index signature allowing any string keys
}

type TsortedBy =
  | "name"
  | "monthly"
  | "weekly"
  | "daily"
  | "status"
  | "profile"
  | "broker";

type TsortOrder = "increase" | "decrease";

const Controllerpage = () => {
  const router = useRouter();
  const { userData } = useUserData();

  useEffect(() => {

  }, [userData, router]);

  const [isLoading, setIsLoading] = useState(false);

  const [changedRiskProfile, setChangedRiskProfile] = useState(false);

  const [usersData, setUsersData] = useState<ControllerColumn[]>([]);

  const [sortedBy, setSortedBy] = useState<TsortedBy>("name");

  const [sortOrder, setSortOrder] = useState<TsortOrder>(
    sortedBy === "name" ? "increase" : "decrease"
  );

  const [maxPageSize, setMaxPageSize] = useState(10);
  const [maxPage, setMaxPage] = useState(1);

  const [queryFilter, setQueryFilter] = useState("");

  const { riskProfiles, setRiskProfiles } = useRiskProfiles();

  const [filteredUsersData, setFilteredUsersData] = useState<
    ControllerColumn[]
  >([]);

  const [currentPage, setCurrentPage] = useState(1);

  // Fetching Risk Profiles from the server for risk profile table
  const fetchRiskProfiles = () => {
    const query = gql`
      query {
        allRiskprofile {
          id
          name
          dailyLossLimitPercentage
          dailyProfitLimitPercentage
          weeklyLossLimitPercentage
          weeklyProfitLimitPercentage
          monthlyLossLimitPercentage
          monthlyProfitLimitPercentage
        }
      }
    `;

    setIsLoading(true);
    client
      .query({
        query: query,
        fetchPolicy: "no-cache",
      })
      .then((response) => {
        setRiskProfiles(response.data.allRiskprofile);
      })
      .catch((error) => {
        console.log(error.message);
      })
      .finally(() => {
        setIsLoading(false);
      });
  };

  // Fetching Risk Profiles from the server for risk profile table
  useEffect(() => {
    fetchRiskProfiles();
  }, []);

  // Fetching User All Brokers from the server for controller table
  const getAllUserData = () => {
    const query = gql`
      query {
        allUserExchanges {
          id
          name
          clientCode
          accountHolderName
          monthlyPnlPercentage
          weeklyPnlPercentage
          dailyPnlPercentage
          status
          riskprofilename
        }
      }
    `;

    setIsLoading(true);

    client
      .query({
        query: query,
        fetchPolicy: "no-cache",
      })
      .then((result) => {
        setUsersData(result.data.allUserExchanges);
      })
      .catch((error) => {
        console.log(error.message);
      })
      .finally(() => {
        setIsLoading(false);
      });
  };

  // change page (pagination)
  const handlePageChange = (newPage: number) => {
    setCurrentPage(newPage);
  };

  // Sorting the data based on the column
  const sortedUsersData = (
    users: ControllerColumn[],
    sortedBy: TsortedBy,
    sortOrder: TsortOrder
  ) => {
    const getValue = (obj: ControllerColumn, field: string) => {
      return (obj[field]);
    };

    const compareStrings = (valueA: string, valueB: string) => {
      return sortOrder === "increase"
        ? valueA.localeCompare(valueB)
        : valueB.localeCompare(valueA);
    };

    const compareNumbers = (valueA: number, valueB: number) => {
      return sortOrder === "increase" ? valueA - valueB : valueB - valueA;
    };

    return users.slice().sort((a, b) => {
      switch (sortedBy) {
        case "name":
          return compareStrings(
            getValue(a, "accountHolderName"),
            getValue(b, "accountHolderName")
          );
        case "monthly":
          return compareNumbers(
            parseFloat(getValue(a, "monthlyPnlPercentage")),
            parseFloat(getValue(b, "monthlyPnlPercentage"))
          );
        case "weekly":
          return compareNumbers(
            parseFloat(getValue(a, "weeklyPnlPercentage")),
            parseFloat(getValue(b, "weeklyPnlPercentage"))
          );
        case "daily":
          return compareNumbers(
            parseFloat(getValue(a, "dailyPnlPercentage")),
            parseFloat(getValue(b, "dailyPnlPercentage"))
          );
        case "status":
          return compareStrings(getValue(a, "status"), getValue(b, "status"));
        case "profile":
          return compareStrings(a.riskprofilename, b.riskprofilename);
        case "broker":
          return compareStrings(getValue(a, "name"), getValue(b, "name"));
        default:
          return 0;
      }
    });
  };

  // Filtering the data based on the query
  useEffect(() => {
    const start = (currentPage - 1) * maxPageSize;
    const end = start + maxPageSize;
    const queryFilteredData = usersData.filter((user) => {
      return (
        (user.name)
          .toLowerCase()
          .includes(queryFilter.toLowerCase()) ||
        (user.clientCode)
          .toLowerCase()
          .includes(queryFilter.toLowerCase()) ||
        (user.accountHolderName)
          .toLowerCase()
          .includes(queryFilter.toLowerCase()) ||
        (user.status)
          .toLowerCase()
          .includes(queryFilter.toLowerCase()) ||
        user.riskprofilename.toLowerCase().includes(queryFilter.toLowerCase())
      );
    });
    setMaxPage(Math.ceil(queryFilteredData.length / maxPageSize));
    const sortedUsers = sortedUsersData(queryFilteredData, sortedBy, sortOrder);
    setFilteredUsersData(sortedUsers.slice(start, end));
  }, [currentPage, usersData, sortedBy, sortOrder, maxPageSize, queryFilter]);

  // Fetching User All Brokers from the server for controller table
  useEffect(() => {
    getAllUserData();
    setChangedRiskProfile(false);
  }, [changedRiskProfile]);

  return (
    <div className="h-full flex flex-col items-start w-full gap-6">
      <div className="flex flex-col">
        <span className="text-base font-semibold">Account Profile</span>
        <span className="text-sm" style={{ color: "var(--tv-text-soft)" }}>
          Risk profiles and account controls
        </span>
      </div>
      <div className="w-full overflow-auto">
        <RiskProfileTable riskProfileData={riskProfiles} />
      </div>
      <div className="w-full flex flex-col gap-4 overflow-auto">
        <div className="flex flex-col md:flex-row md:items-center justify-between w-full gap-4 p-2">
          <div className="text-base font-semibold">Users Risk Profile</div>
          <div className="flex flex-col sm:flex-row md:items-center justify-between gap-4">
            <div className="flex items-center gap-5">
              <input
                type="text"
                placeholder="Search"
                value={queryFilter}
                onChange={(e) => {
                  setQueryFilter(e.target.value);
                  setCurrentPage(1);
                }}
                className="w-[200px]"
                style={{
                  background: "var(--tv-bg)",
                  border: "1px solid var(--tv-border)",
                  borderRadius: "6px",
                  padding: "6px 10px",
                  fontSize: "13px",
                  color: "inherit",
                }}
              />
              <Button
                size="sm"
                onClick={() => {
                  getAllUserData();
                }}
              >
                Refresh
              </Button>
            </div>
            <div>
              <Select
                onValueChange={(value: string) => {
                  setMaxPageSize(parseInt(value));
                  setCurrentPage(1);
                }}
              >
                <SelectTrigger
                  className="w-[150px]"
                  name="expiry-selector"
                >
                  <SelectValue placeholder={maxPageSize.toString()} />
                </SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    <SelectItem value={(10).toString()}>10</SelectItem>
                    <SelectItem value={(25).toString()}>25</SelectItem>
                    <SelectItem value={(50).toString()}>50</SelectItem>
                    <SelectItem value={(100).toString()}>100</SelectItem>
                  </SelectGroup>
                </SelectContent>
              </Select>
            </div>
          </div>
        </div>
        <DataTable
          data={filteredUsersData}
          currentPage={currentPage}
          maxPageSize={maxPageSize}
          setChangedRiskProfile={setChangedRiskProfile}
          setSortedBy={setSortedBy}
          setSortOrder={setSortOrder}
          sortOrder={sortOrder}
          sortedBy={sortedBy}
        />
        <div className="flex items-center justify-center gap-4">
          {Array.from({ length: maxPage }, (_, i) => i + 1).map((item) => (
            <Button
              key={item}
              size="sm"
              variant={item === currentPage ? "default" : "ghost"}
              onClick={() => handlePageChange(item)}
            >
              {item}
            </Button>
          ))}
        </div>
      </div>
    </div>
  );
};

export default Controllerpage;
