import type { DateRange } from "@/lib/api";

export type Period = "this_month" | "last_month" | "year_to_date" | "custom";

function toISODate(d: Date): string {
  return d.toISOString().slice(0, 10);
}

/** customMonth is a "YYYY-MM" string, only used when period === "custom". */
export function getDateRange(period: Period, customMonth?: string): DateRange {
  const today = new Date();

  if (period === "last_month") {
    const start = new Date(today.getFullYear(), today.getMonth() - 1, 1);
    const end = new Date(today.getFullYear(), today.getMonth(), 0);
    return { startDate: toISODate(start), endDate: toISODate(end) };
  }

  if (period === "year_to_date") {
    const start = new Date(today.getFullYear(), 0, 1);
    return { startDate: toISODate(start), endDate: toISODate(today) };
  }

  if (period === "custom" && customMonth) {
    const [year, month] = customMonth.split("-").map(Number);
    const start = new Date(year, month - 1, 1);
    const lastDayOfMonth = new Date(year, month, 0);
    // Don't project into the future if the user picks the current month
    const end = lastDayOfMonth < today ? lastDayOfMonth : today;
    return { startDate: toISODate(start), endDate: toISODate(end) };
  }

  // this_month (default)
  const start = new Date(today.getFullYear(), today.getMonth(), 1);
  return { startDate: toISODate(start), endDate: toISODate(today) };
}

export function periodLabel(period: Period, customMonth?: string): string {
  switch (period) {
    case "last_month":
      return "Last month";
    case "year_to_date":
      return "Year to date";
    case "custom": {
      if (!customMonth) return "Custom month";
      const [year, month] = customMonth.split("-").map(Number);
      // Use the local-time constructor (not a "YYYY-MM-DD" string, which parses as UTC
      // and can display as the wrong month in timezones behind UTC).
      return new Date(year, month - 1, 1).toLocaleDateString("en-US", {
        month: "long",
        year: "numeric",
      });
    }
    default:
      return "This month";
  }
}
