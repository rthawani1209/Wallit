"use client";

import { useState } from "react";
import { PiggyBank, Sparkles } from "lucide-react";
import { Card } from "@/components/ui/Card";
import type { Plan } from "@/lib/api";

function fmt(val: number) {
  return val.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
}

function fmtDate(iso: string) {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

export function SavingsGoals({
  data,
  onArchive,
}: {
  data: Plan[];
  onArchive: (id: string) => Promise<void>;
}) {
  const [archiving, setArchiving] = useState<string | null>(null);

  async function handleArchive(id: string) {
    setArchiving(id);
    try {
      await onArchive(id);
    } finally {
      setArchiving(null);
    }
  }

  return (
    <Card className="p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="font-semibold text-[15px] tracking-tight">Savings Goals</h2>
          <p className="text-xs text-muted-foreground mt-0.5">Tracked at your pledged monthly pace</p>
        </div>
        <PiggyBank className="w-4 h-4 text-primary" />
      </div>

      {data.length === 0 ? (
        <div className="text-center py-6">
          <Sparkles className="w-5 h-5 text-muted-foreground mx-auto mb-2" />
          <p className="text-muted-foreground text-sm">
            No savings goals yet — ask the Assistant to help you set one up.
          </p>
        </div>
      ) : (
        <div className="space-y-5">
          {data.map((goal) => {
            const pct = Math.min(100, Math.round(goal.progress_pct));
            const color = goal.is_achieved ? "#10d98c" : goal.on_track === false ? "#f59e0b" : "#10d98c";
            const statusLabel = goal.is_achieved
              ? "Achieved!"
              : goal.on_track === false
                ? "Behind pace"
                : goal.on_track === true
                  ? "On track"
                  : null;
            const statusColor = goal.is_achieved || goal.on_track ? "text-primary" : "text-amber-500";

            return (
              <div key={goal.id}>
                <div className="flex items-center justify-between mb-1.5 gap-3">
                  <span className="font-medium text-sm truncate">{goal.name}</span>
                  <span className="text-sm font-mono shrink-0">
                    <span className="text-foreground">{fmt(goal.saved_amount)}</span>
                    <span className="text-muted-foreground"> / {fmt(goal.target_amount)}</span>
                  </span>
                </div>
                <div className="h-1.5 rounded-full bg-secondary overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all"
                    style={{ width: `${pct}%`, background: color }}
                  />
                </div>
                <div className="flex items-center justify-between mt-1.5 text-xs text-muted-foreground">
                  <span className="flex items-center gap-1.5">
                    {pct}%
                    {statusLabel && <span className={statusColor}>· {statusLabel}</span>}
                  </span>
                  <span>
                    {goal.is_achieved ? (
                      <button
                        onClick={() => handleArchive(goal.id)}
                        disabled={archiving === goal.id}
                        className="text-primary hover:underline disabled:opacity-40 disabled:pointer-events-none"
                      >
                        {archiving === goal.id ? "Archiving…" : "Mark complete"}
                      </button>
                    ) : goal.target_date ? (
                      `Target: ${fmtDate(goal.target_date)}`
                    ) : goal.projected_completion_date ? (
                      `Est. ${fmtDate(goal.projected_completion_date)}`
                    ) : null}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </Card>
  );
}
