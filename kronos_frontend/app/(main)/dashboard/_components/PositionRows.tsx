// React - Next default
import React from "react";

// Icons
import { LuClipboardList } from "react-icons/lu";

// Utils
import { formatCapitalWithoutSymbol } from "@/utils/FormatCapital";
import { dateFormatter } from "@/utils/dateFormatter";
import { formatTime12h } from "@/utils/format";

// Types
import { PositionProps } from "@/types";

// XAUUSD: 1 lot = 100 oz. Same contract size the backend applies to totalValue /
// profitLoss, so the order Amount column agrees with the position notional.
const CONTRACT_SIZE = 100;

// Components
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

import { Button } from "@/components/ui/button";

interface PositionRowsProps {
  pos: PositionProps;
}


const PositionRows: React.FC<PositionRowsProps> = ({ pos }) => {
  let profitLossColor = "text-up";

  if ((pos.profitLoss) < 0) {
    profitLossColor = "text-down";
  }

  return (
    <div
      className="flex items-center w-full mt-4 p-2 hover:bg-[var(--tv-surface-2)]"
      style={{ borderBottom: "1px solid var(--tv-border)", minHeight: "36px" }}
    >
      <div className="flex items-center gap-4 w-1/4">
        <Dialog>
          <DialogTrigger asChild>
            <Button className="p-0 bg-transparent hover:bg-transparent h-max flex items-center gap-2 text-[10px] md:text-[12px] xl:text-sm" style={{ color: "var(--tv-text-1)" }}>
              {pos.symbol} <LuClipboardList className="inline-block" />
            </Button>
          </DialogTrigger>
          <DialogContent className="h-auto max-w-screen-lg lg:min-w-max flex flex-col">
            <DialogHeader>
              <DialogTitle className="text-[10px] md:text-[12px] xl:text-sm">
                Order Details of {pos.symbol}
              </DialogTitle>
            </DialogHeader>
            <DialogDescription className="overflow-y-auto">
              <div className="max-h-[26rem] overflow-y-auto">
                <Table className="text-[10px] md:text-[12px] xl:text-sm">
                  <TableHeader className="w-full">
                    <TableRow className="hover:bg-[var(--tv-surface-2)]">
                      <TableHead className="">Date</TableHead>
                      <TableHead className="">Time</TableHead>
                      <TableHead className="">Condition</TableHead>
                      <TableHead className="">Instrument Symbol</TableHead>
                      <TableHead className="">Quantity</TableHead>
                      <TableHead className="">Price $</TableHead>
                      <TableHead className="">Amount $</TableHead>
                      <TableHead className="">Reason</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody className="w-full">
                    {pos.Orders.map((order) => (
                      <TableRow
                        key={order.id}
                        className="w-full hover:bg-[var(--tv-surface-2)]"
                      >
                        <TableCell>{dateFormatter(order.createdAt)}</TableCell>
                        <TableCell>{formatTime12h(order.createdAt)}</TableCell>
                        <TableCell>{order.condition}</TableCell>
                        <TableCell>{order.symbol}</TableCell>
                        <TableCell className="tnum">{order.quantity}</TableCell>
                        <TableCell className="tnum">{order.price}</TableCell>
                        <TableCell className="tnum">
                          {formatCapitalWithoutSymbol(
                            Number(order.quantity) *
                              Number.parseFloat(order.price) *
                              CONTRACT_SIZE
                          )}
                        </TableCell>
                        <TableCell>{order.reason}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </DialogDescription>
          </DialogContent>
        </Dialog>
      </div>
      <div className="tnum flex items-center gap-4 w-1/12">{pos.quantity}</div>
      <div className="tnum flex items-center gap-4 w-1/6">{pos.ltp}</div>
      <div className="tnum flex items-center gap-4 w-1/6">{pos.avgBuyPrice}</div>
      <div className="tnum flex items-center gap-4 w-1/6">
        {formatCapitalWithoutSymbol(pos.totalValue)}
      </div>
      <div
        className={`tnum flex items-center gap-4 font-semibold w-1/6 ${profitLossColor}`}
      >
        <Dialog>

          <DialogTrigger asChild>

            <Button className={`bg-transparent hover:bg-transparent p-0 h-auto flex items-center gap-4 font-semibold shadow-none ${profitLossColor}`}>
              {Number(pos.profitLoss).toFixed(2)}
            </Button>
          </DialogTrigger>
          <DialogContent className="h-auto max-w-screen-lg lg:min-w-max flex flex-col">
            <DialogHeader>
              <DialogTitle className="text-[10px] md:text-[12px] xl:text-sm">
                Trigger Details of {pos.symbol}
              </DialogTitle>
            </DialogHeader>
            <DialogDescription className="overflow-y-auto">
              <div className="max-h-[26rem] overflow-y-auto">
                <Table className="text-[10px] md:text-[12px] xl:text-sm">
                  <TableHeader className="w-full">
                    <TableRow className="hover:bg-[var(--tv-surface-2)]">
                      <TableHead className="">Date</TableHead>
                      <TableHead className="">Time</TableHead>
                      <TableHead className="">Condition</TableHead>
                      <TableHead className="">Quantity</TableHead>
                      <TableHead className="">Trigger Price</TableHead>
                      <TableHead className="">Status</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody className="w-full">
                    {pos.triggers.map((trigger) => (
                        <TableRow
                            key={trigger.id}
                            className="w-full hover:bg-[var(--tv-surface-2)]"
                        >
                          <TableCell>{dateFormatter(trigger.createdAt)}</TableCell>
                          <TableCell>{formatTime12h(trigger.modifiedAt)}</TableCell>
                          <TableCell>{trigger.triggerType}</TableCell>
                          <TableCell className="tnum">{trigger.quantity}</TableCell>
                          <TableCell className="tnum">{trigger.triggerPrice}</TableCell>
                          <TableCell>
                            {trigger.status}
                          </TableCell>

                        </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </DialogDescription>
          </DialogContent>

        </Dialog>      </div>
    </div>
  );
};

export default PositionRows;
