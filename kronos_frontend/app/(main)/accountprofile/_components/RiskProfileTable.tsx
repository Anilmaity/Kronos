import * as React from "react";

// Components
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { RiskProfileTableData } from "./main";

const cellBorder: React.CSSProperties = { borderColor: "var(--tv-border)" };

const RiskProfileTable = ({
  riskProfileData,
}: {
  riskProfileData: RiskProfileTableData[];
}) => {
  return (
    <div className="w-full flex flex-col gap-4">
      <div className="flex items-center justify-between w-full">
        <div className="text-base font-semibold">Risk Profiles</div>
      </div>
      <Table className="text-[10px] md:text-[12px] xl:text-sm">
        <TableHeader>
          <TableRow className="hover:bg-background">
            <TableHead rowSpan={2} className="border text-center" style={cellBorder}>
              Name
            </TableHead>
            <TableHead colSpan={2} className="border text-center" style={cellBorder}>
              Daily
            </TableHead>
            <TableHead colSpan={2} className="border text-center" style={cellBorder}>
              Weekly
            </TableHead>
            <TableHead colSpan={2} className="border text-center" style={cellBorder}>
              Monthly
            </TableHead>
          </TableRow>
          <TableRow className="hover:bg-background">
            <TableHead className="border text-center font-semibold" style={{ ...cellBorder, color: "var(--tv-down)" }}>
              Loss
            </TableHead>
            <TableHead className="border text-center font-semibold" style={{ ...cellBorder, color: "var(--tv-up)" }}>
              Profit
            </TableHead>
            <TableHead className="border text-center font-semibold" style={{ ...cellBorder, color: "var(--tv-down)" }}>
              Loss
            </TableHead>
            <TableHead className="border text-center font-semibold" style={{ ...cellBorder, color: "var(--tv-up)" }}>
              Profit
            </TableHead>
            <TableHead className="border text-center font-semibold" style={{ ...cellBorder, color: "var(--tv-down)" }}>
              Loss
            </TableHead>
            <TableHead className="border text-center font-semibold" style={{ ...cellBorder, color: "var(--tv-up)" }}>
              Profit
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {riskProfileData.map((riskProfile) => (
            <TableRow key={riskProfile.id}>
              <TableCell className="border text-center" style={cellBorder}>
                {riskProfile.name}
              </TableCell>
              <TableCell className="border text-center" style={cellBorder}>
                {parseFloat(riskProfile.dailyLossLimitPercentage) * 100} %
              </TableCell>
              <TableCell className="border text-center" style={cellBorder}>
                {parseFloat(riskProfile.dailyProfitLimitPercentage) * 100} %
              </TableCell>
              <TableCell className="border text-center" style={cellBorder}>
                {parseFloat(riskProfile.weeklyLossLimitPercentage) * 100} %
              </TableCell>
              <TableCell className="border text-center" style={cellBorder}>
                {parseFloat(riskProfile.weeklyProfitLimitPercentage) * 100} %
              </TableCell>
              <TableCell className="border text-center" style={cellBorder}>
                {parseFloat(riskProfile.monthlyLossLimitPercentage) * 100} %
              </TableCell>
              <TableCell className="border text-center" style={cellBorder}>
                {parseFloat(riskProfile.monthlyProfitLimitPercentage) * 100} %
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
};

export default RiskProfileTable;
