/**
 * Compact capital formatter shared by all three public wrappers.
 * Output is identical to the previous three near-duplicate implementations:
 *   < 1k      → raw number            (e.g. "999.5")
 *   < 1 lakh  → floored thousands     (e.g. "99k")
 *   < 1 crore → lakhs, 2 dp trimmed   (e.g. "1.5L")
 *   otherwise → crores, 2 dp trimmed  (e.g. "1.25Cr")
 * Non-finite input renders as 0.
 */
const formatCapitalCore = (capital: number, prefix: string): string => {
  if (!Number.isFinite(capital)) return `${prefix}0`;
  const sign = Math.sign(capital);
  const minus = sign === -1 ? "-" : "";
  const absCapital = Math.abs(capital);
  if (absCapital < 1000) {
    return `${prefix}${minus}${absCapital}`;
  } else if (absCapital < 100000) {
    return `${prefix}${minus}${Math.floor(absCapital / 1000)}k`;
  } else if (absCapital < 10000000) {
    return `${prefix}${minus}${Number((absCapital / 100000).toFixed(2))}L`;
  } else {
    return `${prefix}${minus}${Number((absCapital / 10000000).toFixed(2))}Cr`;
  }
};

export const formatCapital = (capital: number) =>
  formatCapitalCore(capital, "$ ");

export const formatCapitalWithoutSymbol = (capital: number) =>
  formatCapitalCore(capital, "");

export const formatCapitalString = (capital: string) =>
  formatCapitalCore(Number(capital), "$ ");
