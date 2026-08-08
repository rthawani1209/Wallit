"use client";

import { AlertTriangle } from "lucide-react";
import { Card } from "@/components/ui/Card";
import type { Anomaly } from "@/lib/api";

function fmt(val: number) {
  return val.toLocaleString("en-US", { style: "currency", currency: "USD" });
}

function fmtDate(iso: string) {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

export function AnomaliesCard({ data }: { data: Anomaly[] }) {
  if (data.length === 0) return null;

  return (
    <Card className="p-6" style={{ borderColor: "rgba(244,63,94,0.2)" }}>
      <div className="flex items-center gap-2 mb-4">
        <AlertTriangle className="w-4 h-4 text-destructive" />
        <h2 className="font-semibold text-[15px] tracking-tight">Unusual Activity</h2>
      </div>
      <div className="space-y-3">
        {data.slice(0, 5).map((a) => (
          <div key={a.id} className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="text-sm font-medium truncate">{a.merchant_name ?? "Unknown merchant"}</p>
              <p className="text-xs text-muted-foreground mt-0.5">{a.anomaly_reason}</p>
            </div>
            <div className="text-right shrink-0">
              <p className="text-sm font-mono font-semibold text-destructive">{fmt(a.amount)}</p>
              <p className="text-[11px] text-muted-foreground">{fmtDate(a.date)}</p>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
