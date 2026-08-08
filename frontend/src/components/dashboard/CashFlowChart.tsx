"use client";

import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { TooltipContentProps } from "recharts/types/component/Tooltip";
import { Card } from "@/components/ui/Card";
import type { CashFlowMonth } from "@/lib/api";

const INCOME_COLOR = "#10d98c";
const EXPENSES_COLOR = "#6366f1";

function fmt(val: number) {
  return val.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
}

function ChartTooltip({ active, payload, label }: TooltipContentProps) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-card border border-border rounded-xl px-4 py-3 text-sm space-y-1.5">
      <div className="text-xs text-muted-foreground mb-1">{label}</div>
      {payload.map((item) => (
        <div key={item.name} className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full shrink-0" style={{ background: item.color }} />
          <span className="font-mono font-medium text-foreground">{fmt(Number(item.value))}</span>
          <span className="text-muted-foreground text-xs capitalize">{item.name}</span>
        </div>
      ))}
    </div>
  );
}

export function CashFlowChart({ data }: { data: CashFlowMonth[] }) {
  const hasData = data.some((d) => d.income > 0 || d.expenses > 0);

  return (
    <Card className="p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="font-semibold text-[15px] tracking-tight">Cash Flow</h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Income vs expenses · last {data.length} months
          </p>
        </div>
        <div className="flex items-center gap-4 text-xs text-muted-foreground">
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full" style={{ background: INCOME_COLOR }} />
            Income
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full" style={{ background: EXPENSES_COLOR }} />
            Expenses
          </span>
        </div>
      </div>

      {!hasData ? (
        <p className="text-muted-foreground text-sm">No transaction history yet.</p>
      ) : (
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="incomeFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={INCOME_COLOR} stopOpacity={0.25} />
                  <stop offset="100%" stopColor={INCOME_COLOR} stopOpacity={0} />
                </linearGradient>
                <linearGradient id="expensesFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={EXPENSES_COLOR} stopOpacity={0.25} />
                  <stop offset="100%" stopColor={EXPENSES_COLOR} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" vertical={false} />
              <XAxis
                dataKey="label"
                tick={{ fill: "#6b7fa3", fontSize: 12 }}
                axisLine={{ stroke: "rgba(255,255,255,0.06)" }}
                tickLine={false}
              />
              <YAxis
                tick={{ fill: "#6b7fa3", fontSize: 12 }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(v) => `$${v >= 1000 ? `${Math.round(v / 1000)}k` : v}`}
                width={44}
              />
              <Tooltip content={ChartTooltip} />
              <Area
                type="monotone"
                dataKey="income"
                name="income"
                stroke={INCOME_COLOR}
                fill="url(#incomeFill)"
                strokeWidth={2}
              />
              <Area
                type="monotone"
                dataKey="expenses"
                name="expenses"
                stroke={EXPENSES_COLOR}
                fill="url(#expensesFill)"
                strokeWidth={2}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </Card>
  );
}
