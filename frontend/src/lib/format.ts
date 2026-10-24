// Dates from the API are calendar dates ("2026-10-01"): formatted in UTC so no time zone
// can move them a day.
const day = new Intl.DateTimeFormat("en-GB", {
  day: "numeric",
  month: "short",
  year: "numeric",
  timeZone: "UTC",
});

/** "2026-10-01" → "1 Oct 2026" */
export const formatDate = (iso: string) => day.format(new Date(`${iso}T00:00:00Z`));
