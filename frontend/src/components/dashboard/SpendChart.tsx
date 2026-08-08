"use client";

import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from "recharts";
import type { TooltipContentProps } from "recharts/types/component/Tooltip";
import { Card } from "@/components/ui/Card";
import type { CategorySpend } from "@/lib/api";

// Matches the chart-1..5 tokens defined in globals.css
const CHART_COLORS = ["#10d98c", "#6366f1", "#f59e0b", "#f43f5e", "#8b5cf6", "#475569"];

function fmt(val: number) {
  return val.toLocaleString("en-US", { style: "currency", currency: "USD" });
}

function ChartTooltip({ active, payload }: TooltipContentProps) {
  if (!active || !payload?.length) return null;
  const item = payload[0];
  return (
    <div className="bg-card border border-border rounded-xl px-4 py-3 text-sm">
      <div className="flex items-center gap-2">
        <span className="w-2 h-2 rounded-full shrink-0" style={{ background: item.color }} />
        <span className="font-mono font-medium text-foreground">{fmt(Number(item.value))}</span>
        <span className="text-muted-foreground text-xs">{item.name}</span>
      </div>
    </div>
  );
}

export function SpendChart({ data }: { data: CategorySpend[] }) {
  const total = data.reduce((sum, d) => sum + d.total, 0);

  return (
    <Card className="p-6 flex flex-col">
      <div className="mb-4">
        <h2 className="font-semibold text-[15px] tracking-tight">Spending</h2>
        <p className="text-xs text-muted-foreground mt-0.5">Month-to-date breakdown</p>
      </div>

      {data.length === 0 ? (
        <p className="text-muted-foreground text-sm">No spending yet this month.</p>
      ) : (
        <>
          <div className="flex justify-center my-2">
            <div className="relative w-[148px] h-[148px]">
              <ResponsiveContainer width={148} height={148}>
                <PieChart>
                  <Pie
                    data={data}
                    dataKey="total"
                    nameKey="category_name"
                    cx="50%"
                    cy="50%"
                    innerRadius={44}
                    outerRadius={68}
                    paddingAngle={2}
                    strokeWidth={0}
                  >
                    {data.map((entry, i) => (
                      <Cell key={entry.category_id ?? "uncategorized"} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip content={ChartTooltip} />
                </PieChart>
              </ResponsiveContainer>
              <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                <span className="text-[10px] text-muted-foreground leading-none mb-1">Total</span>
                <span className="text-sm font-bold leading-none font-mono">{fmt(total)}</span>
              </div>
            </div>
          </div>

          <div className="space-y-2 mt-2 flex-1">
            {data.map((d, i) => (
              <div key={d.category_id ?? "uncategorized"} className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2 min-w-0">
                  <span
                    className="w-2 h-2 rounded-full shrink-0"
                    style={{ background: CHART_COLORS[i % CHART_COLORS.length] }}
                  />
                  <span className="text-muted-foreground truncate">{d.category_name}</span>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <span className="font-mono text-foreground">{fmt(d.total)}</span>
                  <span className="text-muted-foreground w-9 text-right">
                    {total > 0 ? Math.round((d.total / total) * 100) : 0}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </Card>
  );
}
