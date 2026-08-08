"use client";

import { Lightbulb, Repeat } from "lucide-react";
import { Card } from "@/components/ui/Card";
import type { Subscription } from "@/lib/api";

function fmt(val: number) {
  return val.toLocaleString("en-US", { style: "currency", currency: "USD" });
}

function fmtDate(iso: string) {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

const INTERVAL_LABELS: Record<string, string> = {
  weekly: "Weekly",
  monthly: "Monthly",
  quarterly: "Quarterly",
  annual: "Annual",
};

const AVATAR_COLORS = ["#10d98c", "#6366f1", "#f59e0b", "#f43f5e", "#8b5cf6"];

function avatarColor(name: string) {
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash);
  return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length];
}

export function SubscriptionCard({ sub }: { sub: Subscription }) {
  const color = avatarColor(sub.merchant_name);

  return (
    <Card className="p-5">
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3 min-w-0">
          <div
            className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0 font-bold text-sm"
            style={{ background: `${color}1a`, color }}
          >
            {sub.merchant_name.slice(0, 1).toUpperCase()}
          </div>
          <div className="min-w-0">
            <p className="font-medium text-sm truncate">{sub.merchant_name}</p>
            <span className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
              {INTERVAL_LABELS[sub.billing_interval] ?? sub.billing_interval}
            </span>
          </div>
        </div>
        <div className="text-right shrink-0">
          <p className="font-mono font-bold text-lg">{fmt(sub.amount)}</p>
          {sub.next_estimated_date && (
            <p className="text-[11px] text-muted-foreground">Next {fmtDate(sub.next_estimated_date)}</p>
          )}
        </div>
      </div>

      {sub.cheaper_alternative ? (
        <div className="flex items-start gap-2 rounded-lg bg-primary/[0.06] border border-primary/10 px-3 py-2.5">
          <Lightbulb className="w-3.5 h-3.5 text-primary shrink-0 mt-0.5" />
          <p className="text-xs text-muted-foreground leading-relaxed">{sub.cheaper_alternative}</p>
        </div>
      ) : (
        <div className="flex items-center gap-2 rounded-lg bg-secondary/40 px-3 py-2.5">
          <Repeat className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
          <p className="text-xs text-muted-foreground">Recurring charge detected</p>
        </div>
      )}
    </Card>
  );
}
