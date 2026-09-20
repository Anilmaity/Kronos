export const getCurrencySymbol = (): string => {
  return String.fromCharCode(0x0024); // U+0024 — dollar sign. XAU trades settle in USD.
};
