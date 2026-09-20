import React from "react";

const KronosMark = ({ size = 28 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 48 48" aria-label="Kronos">
    <rect x="12" y="10" width="6" height="28" rx="1.5" fill="#2962FF" />
    <rect x="27" y="8" width="6" height="12" rx="1.5" fill="#089981" />
    <rect x="29.5" y="4" width="1" height="4" fill="#089981" />
    <rect x="27" y="28" width="6" height="12" rx="1.5" fill="#F23645" />
    <rect x="29.5" y="40" width="1" height="4" fill="#F23645" />
    <path
      d="M18 24 L27 13 M18 24 L27 35"
      stroke="currentColor"
      strokeWidth="3"
      strokeLinecap="round"
      fill="none"
    />
  </svg>
);

const Logo = ({
  size = 28,
  withWordmark = true,
}: {
  size?: number;
  withWordmark?: boolean;
}) => (
  <div
    className="flex items-center gap-2.5 select-none"
    style={{ color: "var(--tv-text-1)" }}
  >
    <KronosMark size={size} />
    {withWordmark && (
      <span
        className="font-sans"
        style={{ fontWeight: 700, fontSize: "1.05rem", letterSpacing: "0.03em" }}
      >
        KRONOS
      </span>
    )}
  </div>
);

export default Logo;
