"use client";

import { useState } from "react";
import { ChevronRight } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import type { BudgetProgress as BudgetProgressItem } from "@/lib/api";

function fmt(val: number) {
  return val.toLocaleString("en-US", { style: "currency", currency: "USD" });
}

const BAR_COLORS = ["#10d98c", "#6366f1", "#f59e0b", "#f43f5e", "#8b5cf6", "#475569"];

export function BudgetProgress({
  data,
  onSetLimit,
}: {
  data: BudgetProgressItem[];
  onSetLimit: (categoryId: string, limit: number) => Promise<void>;
}) {
  const [managing, setManaging] = useState(false);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState<string | null>(null);

  async function handleSave(categoryId: string) {
    const raw = drafts[categoryId];
    const value = Number(raw);
    if (!raw || !Number.isFinite(value) || value <= 0) return;
    setSaving(categoryId);
    try {
      await onSetLimit(categoryId, value);
      setDrafts((prev) => {
        const next = { ...prev };
        delete next[categoryId];
        return next;
      });
    } finally {
      setSaving(null);
    }
  }

  return (
    <Card className="p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="font-semibold text-[15px] tracking-tight">Budget Progress</h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            {new Date().toLocaleDateString("en-US", { month: "long" })} · day {new Date().getDate()}
          </p>
        </div>
        <button
          onClick={() => setManaging((m) => !m)}
          className="text-primary text-sm font-medium flex items-center gap-0.5 hover:underline"
        >
          {managing ? "Done" : "Manage"}
          {!managing && <ChevronRight className="w-3.5 h-3.5" />}
        </button>
      </div>

      {data.length === 0 ? (
        <p className="text-muted-foreground text-sm">No spending yet this month.</p>
      ) : (
        <div className="space-y-5">
          {data.map((b, i) => {
            const pct = b.limit > 0 ? Math.min(100, Math.round((b.spent / b.limit) * 100)) : 0;
            const over = b.spent > b.limit;
            const color = over ? "#f43f5e" : BAR_COLORS[i % BAR_COLORS.length];
            return (
              <div key={b.category_id}>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="font-medium text-sm">{b.category_name}</span>
                  {managing ? (
                    <div className="flex items-center gap-2">
                      <span className="text-muted-foreground text-xs font-mono">$</span>
                      <input
                        type="number"
                        min={1}
                        placeholder={String(b.limit)}
                        value={drafts[b.category_id] ?? ""}
                        onChange={(e) =>
                          setDrafts((prev) => ({ ...prev, [b.category_id]: e.target.value }))
                        }
                        className="w-20 bg-transparent border border-border rounded-md px-2 py-1 text-xs font-mono text-foreground focus:outline-none focus:ring-2 focus:ring-ring/50"
                      />
                      <button
                        onClick={() => handleSave(b.category_id)}
                        disabled={saving === b.category_id || !drafts[b.category_id]}
                        className="text-primary text-xs font-medium disabled:opacity-40 disabled:pointer-events-none hover:underline"
                      >
                        {saving === b.category_id ? "Saving…" : "Save"}
                      </button>
                    </div>
                  ) : (
                    <span className="text-sm font-mono">
                      <span className={over ? "text-destructive" : "text-foreground"}>{fmt(b.spent)}</span>
                      <span className="text-muted-foreground"> / {fmt(b.limit)}</span>
                    </span>
                  )}
                </div>
                <div className="h-1.5 rounded-full bg-secondary overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all"
                    style={{ width: `${pct}%`, background: color }}
                  />
                </div>
                <div className="flex items-center justify-between mt-1.5 text-xs text-muted-foreground">
                  <span>{pct}% used{!b.is_custom && !managing ? " · suggested" : ""}</span>
                  <span>
                    {over
                      ? `${fmt(b.spent - b.limit)} over`
                      : `${fmt(b.limit - b.spent)} remaining`}
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
