export const dateFormatter = (date: string) => {
  const d = new Date(date);
  const day = d.getDate();
  const month = d.getMonth() + 1;
  const year = d.getFullYear();
  return `${day}/${month}/${year}`;
};

export const dateFromTimestamp = (timestamp: number) => {
  const date = new Date(timestamp);
  const day = date.getDate().toString().padStart(2, "0");
  const month = (date.getMonth() + 1).toString().padStart(2, "0"); // Months are zero-based, so we add 1
  const year = date.getFullYear();
  return `${day}/${month}/${year}`;
};

// YYYY-MM-DD of a Date in the USER'S local time zone. Never use
// toISOString() for a calendar day: it converts to UTC, so in India (UTC+5:30)
// a date picked at local midnight became the PREVIOUS day (picking 27 showed
// "26" on the dashboard while the data was for the 27th).
export const localDateKey = (d: Date): string =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;

// d/m/yyyy label of a Date in the user's local time zone.
export const formatLocalDate = (d: Date): string => `${d.getDate()}/${d.getMonth() + 1}/${d.getFullYear()}`;
