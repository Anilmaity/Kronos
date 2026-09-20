export const formatNumber = (number: number) => {
  if (isNaN(number)) {
    return "Invalid Number";
  }

  // Extract the sign from the number
  const sign = number < 0 ? "-" : "";
  number = Math.abs(number);

  // Define the symbols for thousands, lakhs, crores, and arab
  const symbols = ["", "k", "l", "cr", "ar"];

  // Determine the appropriate symbol based on the magnitude of the number
  let symbolIndex = 0;
  while (number >= 1000) {
    number /= 1000;
    symbolIndex++;
  }

  // Format the number with up to one decimal place
  const formattedNumber = Number(number.toFixed(1));
  // Add the sign and symbol to the formatted number
  const result = `${sign}${formattedNumber}${symbols[symbolIndex]}`;

  return result;
};
