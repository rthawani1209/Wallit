"use client";

import type { Period } from "@/lib/dateRange";

interface PeriodSelectorProps {
  period: Period;
  customMonth: string;
  onPeriodChange: (period: Period) => void;
  onCustomMonthChange: (month: string) => void;
}

export function PeriodSelector({
  period,
  customMonth,
  onPeriodChange,
  onCustomMonthChange,
}: PeriodSelectorProps) {
  return (
    <div className="flex items-center gap-2">
      <select
        value={period}
        onChange={(e) => onPeriodChange(e.target.value as Period)}
        className="text-sm bg-transparent border border-border rounded-md px-2 py-1.5 text-foreground focus:outline-none focus:ring-2 focus:ring-ring/50"
      >
        <option value="this_month" className="bg-card">This month</option>
        <option value="last_month" className="bg-card">Last month</option>
        <option value="year_to_date" className="bg-card">Year to date</option>
        <option value="custom" className="bg-card">Custom month…</option>
      </select>
      {period === "custom" && (
        <input
          type="month"
          value={customMonth}
          onChange={(e) => onCustomMonthChange(e.target.value)}
          max={new Date().toISOString().slice(0, 7)}
          className="text-sm bg-transparent border border-border rounded-md px-2 py-1.5 text-foreground focus:outline-none focus:ring-2 focus:ring-ring/50"
        />
      )}
    </div>
  );
}
