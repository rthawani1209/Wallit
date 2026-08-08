"use client";

import { Card } from "@/components/ui/Card";
import type { UpcomingBill } from "@/lib/api";

function fmt(val: number) {
  return val.toLocaleString("en-US", { style: "currency", currency: "USD" });
}

function fmtDate(iso: string) {
  // Parse as a plain calendar date, not a UTC instant, so it doesn't shift a day off.
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

export function UpcomingBills({ data }: { data: UpcomingBill[] }) {
  const now = new Date();
  const thisMonthTotal = data
    .filter((b) => {
      const [y, m] = b.next_due_date.split("-").map(Number);
      return y === now.getFullYear() && m === now.getMonth() + 1;
    })
    .reduce((sum, b) => sum + b.amount, 0);

  return (
    <Card className="p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-semibold text-[15px] tracking-tight">Upcoming Bills</h2>
        {data.length > 0 && (
          <span
            className="text-[10px] font-semibold uppercase tracking-wide rounded-full px-2.5 py-1"
            style={{ background: "rgba(245,158,11,0.12)", color: "#f59e0b" }}
          >
            Next 45 days
          </span>
        )}
      </div>

      {data.length === 0 ? (
        <p className="text-muted-foreground text-sm">
          No recurring bills detected yet — they show up here once a charge repeats a couple of months in a row.
        </p>
      ) : (
        <>
          <div className="space-y-3.5">
            {data.map((b) => (
              <div key={b.merchant_name} className="flex items-center gap-3">
                <span className="w-1.5 h-1.5 rounded-full shrink-0" style={{ background: "#f59e0b" }} />
                <span className="text-sm text-muted-foreground flex-1 truncate">{b.merchant_name}</span>
                <span className="text-xs text-muted-foreground shrink-0">{fmtDate(b.next_due_date)}</span>
                <span className="text-sm font-mono font-medium shrink-0 w-20 text-right">{fmt(b.amount)}</span>
              </div>
            ))}
          </div>
          <div className="flex items-center justify-between mt-5 pt-4 border-t border-border text-sm">
            <span className="text-muted-foreground">Total due this month</span>
            <span className="font-mono font-semibold" style={{ color: "#f59e0b" }}>
              {fmt(thisMonthTotal)}
            </span>
          </div>
        </>
      )}
    </Card>
  );
}
