import { UserStrategysProps } from "@/types";

// Strategy families that get their own dashboard tab.
export type StrategySource = "neymar" | "neymar-vip";

// Platform Strategy rows provisioned by KronosStrategies/Telegram_Bot
// (apis_persist.py, deploy_dashboard_account2.py, deploy_neymar_vip.py).
// Keep in sync with Kronos_Backend/apis/copy_trade.py.
export const SOURCE_STRATEGY_IDS: Record<StrategySource, string[]> = {
  neymar: [
    "d9bf1604-9ee0-4454-b3c1-b7335ff8915f", // Neymar Telegram Copy
    "30427449-9705-406c-820d-2b5ff9d8c003", // Neymar Telegram Copy (Account 2)
  ],
  "neymar-vip": [
    "c708a216-5c5f-41b4-a63b-7e13d15ce090", // Neymar VIP
  ],
};

// Name fallback for rows provisioned outside those scripts.
const SOURCE_NAME_PREFIX: Record<StrategySource, string> = {
  neymar: "neymar telegram copy",
  "neymar-vip": "neymar vip",
};

export const matchesSource = (
  userStrategy: UserStrategysProps,
  source: StrategySource
): boolean =>
  SOURCE_STRATEGY_IDS[source].includes(userStrategy.strategy?.id) ||
  (userStrategy.name ?? "").toLowerCase().startsWith(SOURCE_NAME_PREFIX[source]);
