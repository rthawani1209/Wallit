"use client";

import { useEffect, useState } from "react";
import { TrendingDown, TrendingUp } from "lucide-react";
import { api, Category, SimulateResult } from "@/lib/api";
import { Card } from "@/components/ui/Card";

function fmt(val: number) {
  return val.toLocaleString("en-US", { style: "currency", currency: "USD" });
}

export function WhatIfSimulator({ categories }: { categories: Category[] }) {
  const [categoryId, setCategoryId] = useState(""); // "" = total spending
  const [percent, setPercent] = useState(0);
  const [result, setResult] = useState<SimulateResult | null>(null);

  useEffect(() => {
    const handle = setTimeout(() => {
      api.simulate(percent, categoryId || undefined)
        .then(setResult)
        .catch(() => {});
    }, 150);
    return () => clearTimeout(handle);
  }, [percent, categoryId]);

  const delta = result ? result.projected_balance - result.current_balance : 0;
  const categoryLabel = categoryId
    ? categories.find((c) => c.id === categoryId)?.name ?? "spending"
    : "total spending";

  return (
    <Card className="p-6">
      <h2 className="font-semibold text-[15px] tracking-tight mb-1">What if…</h2>
      <p className="text-xs text-muted-foreground mb-5">
        Drag the slider to see how a spending change would affect your balance.
      </p>

      <div className="flex flex-wrap items-center gap-3 mb-5">
        <span className="text-sm text-foreground">Change</span>
        <select
          value={categoryId}
          onChange={(e) => setCategoryId(e.target.value)}
          className="text-sm bg-transparent border border-border rounded-md px-2 py-1.5 text-foreground focus:outline-none focus:ring-2 focus:ring-ring/50"
        >
          <option value="" className="bg-card">Total spending</option>
          {categories.map((c) => (
            <option key={c.id} value={c.id} className="bg-card">
              {c.name}
            </option>
          ))}
        </select>
        <span className="text-sm text-foreground">by</span>
        <span
          className={`text-sm font-mono font-semibold ${percent < 0 ? "text-primary" : percent > 0 ? "text-destructive" : "text-foreground"}`}
        >
          {percent > 0 ? "+" : ""}
          {percent}%
        </span>
      </div>

      <input
        type="range"
        min={-80}
        max={80}
        step={5}
        value={percent}
        onChange={(e) => setPercent(Number(e.target.value))}
        className="w-full accent-primary mb-3"
      />

      {result && (
        <p className="text-xs text-muted-foreground mb-3">
          Based on {fmt(result.actual_month_spend)} spent on {categoryLabel} so far this month — the
          percentage applies to that amount, not your total balance.
        </p>
      )}

      {result && (
        <div className="flex items-center justify-between rounded-xl bg-secondary/50 px-4 py-3">
          <div>
            <p className="text-xs text-muted-foreground">
              Projected balance if you {percent < 0 ? "cut" : percent > 0 ? "increase" : "keep"}{" "}
              {categoryLabel} {percent !== 0 && `by ${Math.abs(percent)}%`}
            </p>
            <p className="text-xl font-bold font-mono mt-1">{fmt(result.projected_balance)}</p>
          </div>
          {percent !== 0 && (
            <div
              className={`flex items-center gap-1 text-sm font-semibold font-mono ${
                delta >= 0 ? "text-primary" : "text-destructive"
              }`}
            >
              {delta >= 0 ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
              {delta >= 0 ? "+" : ""}
              {fmt(delta)}
            </div>
          )}
        </div>
      )}
    </Card>
  );
}
