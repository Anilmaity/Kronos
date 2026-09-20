// React - Next default
import { formatCapital } from "@/utils/FormatCapital";
import React from "react";

// Icons
import { IconType } from "react-icons";

export interface SummaryBoxDataType {
  icon: IconType;
  title: string;
  value: string;
  bgColor: string;
  iconColor: string;
  indicator?: string;
}

const DashboardSummaryBox: React.FC<SummaryBoxDataType> = ({
  icon: Icon,
  title,
  value,
  bgColor,
  iconColor,
  indicator = "number",
}) => {
  const numericVal = parseFloat(value);
  const valueColor =
    numericVal > 0
      ? "var(--tv-up)"
      : numericVal < 0
      ? "var(--tv-down)"
      : "var(--tv-text-1)";

  return (
    <div
      className="w-full flex gap-5 p-5 items-center justify-normal h-full"
      style={{
        background: "var(--tv-surface)",
        border: "1px solid var(--tv-border)",
        borderRadius: "8px",
      }}
    >
      <div
        className="w-[60px] h-[60px] rounded-full flex items-center justify-center flex-shrink-0"
        style={{ background: "var(--tv-surface-2)" }}
      >
        <Icon size={26} style={{ color: "var(--tv-text-2)" }} />
      </div>
      <div className="w-full flex flex-col gap-1">
        <div
          className="tnum"
          style={{ fontSize: "20px", fontWeight: 700, color: valueColor }}
        >
          {indicator === "inr" ? formatCapital(parseFloat(value)) : value}
        </div>
        <div
          style={{
            fontSize: "11px",
            fontWeight: 500,
            textTransform: "uppercase",
            letterSpacing: "0.4px",
            color: "var(--tv-text-3)",
          }}
        >
          {title}
        </div>
      </div>
    </div>
  );
};

export default DashboardSummaryBox;
