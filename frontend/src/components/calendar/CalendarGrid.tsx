"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";
import { Card } from "@/components/ui/Card";
import type { CalendarEvent } from "@/lib/api";

const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

function fmt(val: number) {
  return val.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
}

function toISODate(d: Date) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function buildWeeks(monthStart: Date): Date[][] {
  const firstOfMonth = new Date(monthStart.getFullYear(), monthStart.getMonth(), 1);
  const gridStart = new Date(firstOfMonth);
  gridStart.setDate(gridStart.getDate() - firstOfMonth.getDay());

  const weeks: Date[][] = [];
  const cursor = new Date(gridStart);
  for (let week = 0; week < 6; week++) {
    const days: Date[] = [];
    for (let day = 0; day < 7; day++) {
      days.push(new Date(cursor));
      cursor.setDate(cursor.getDate() + 1);
    }
    weeks.push(days);
    // Stop once we've completed the month and filled its last week.
    if (cursor.getMonth() !== monthStart.getMonth() && cursor > firstOfMonth) break;
  }
  return weeks;
}

interface CalendarGridProps {
  monthStart: Date;
  events: CalendarEvent[];
  selectedDate: string | null;
  onSelectDate: (iso: string) => void;
  onPrevMonth: () => void;
  onNextMonth: () => void;
}

export function CalendarGrid({
  monthStart,
  events,
  selectedDate,
  onSelectDate,
  onPrevMonth,
  onNextMonth,
}: CalendarGridProps) {
  const weeks = buildWeeks(monthStart);
  const todayISO = toISODate(new Date());

  const eventsByDate = new Map<string, CalendarEvent[]>();
  for (const e of events) {
    const list = eventsByDate.get(e.date) ?? [];
    list.push(e);
    eventsByDate.set(e.date, list);
  }

  return (
    <Card className="p-5">
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-semibold text-base">
          {monthStart.toLocaleDateString("en-US", { month: "long", year: "numeric" })}
        </h2>
        <div className="flex items-center gap-1">
          <button
            onClick={onPrevMonth}
            aria-label="Previous month"
            className="w-8 h-8 flex items-center justify-center rounded-md hover:bg-secondary transition-colors text-muted-foreground hover:text-foreground"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <button
            onClick={onNextMonth}
            aria-label="Next month"
            className="w-8 h-8 flex items-center justify-center rounded-md hover:bg-secondary transition-colors text-muted-foreground hover:text-foreground"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div className="grid grid-cols-7 gap-1.5 mb-1.5">
        {WEEKDAYS.map((w) => (
          <div key={w} className="text-center text-[10px] font-semibold uppercase tracking-wide text-muted-foreground py-1">
            {w}
          </div>
        ))}
      </div>

      <div className="grid grid-cols-7 gap-1.5">
        {weeks.flat().map((day) => {
          const iso = toISODate(day);
          const inMonth = day.getMonth() === monthStart.getMonth();
          const dayEvents = eventsByDate.get(iso) ?? [];
          const isToday = iso === todayISO;
          const isSelected = iso === selectedDate;

          return (
            <button
              key={iso}
              onClick={() => dayEvents.length > 0 && onSelectDate(iso)}
              className={`relative aspect-square sm:aspect-auto sm:h-24 rounded-lg border p-1.5 text-left transition-colors flex flex-col ${
                isSelected
                  ? "border-primary bg-primary/[0.08]"
                  : "border-white/[0.05] hover:border-white/[0.12]"
              } ${inMonth ? "bg-white/[0.015]" : "bg-transparent opacity-40"} ${
                dayEvents.length > 0 ? "cursor-pointer" : "cursor-default"
              }`}
            >
              <span
                className={`text-xs font-mono ${
                  isToday
                    ? "w-5 h-5 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-bold"
                    : "text-muted-foreground"
                }`}
              >
                {day.getDate()}
              </span>
              <div className="mt-1 space-y-0.5 overflow-hidden flex-1">
                {dayEvents.slice(0, 2).map((e, i) => (
                  <div
                    key={i}
                    className="text-[9px] sm:text-[10px] leading-tight rounded px-1 py-0.5 truncate bg-primary/10 text-primary font-medium"
                  >
                    {e.merchant_name} {fmt(e.amount)}
                  </div>
                ))}
                {dayEvents.length > 2 && (
                  <div className="text-[9px] text-muted-foreground px-1">+{dayEvents.length - 2} more</div>
                )}
              </div>
            </button>
          );
        })}
      </div>
    </Card>
  );
}
