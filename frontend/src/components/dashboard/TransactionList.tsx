"use client";

import { useState } from "react";
import { ArrowDownLeft, ArrowUpRight } from "lucide-react";
import { api, Category, Transaction } from "@/lib/api";
import { Card } from "@/components/ui/Card";

interface TransactionListProps {
  transactions: Transaction[];
  categories: Category[];
  onCategoryChange: (transactionId: string, categoryId: string) => void;
}

export function TransactionList({ transactions, categories, onCategoryChange }: TransactionListProps) {
  return (
    <Card className="p-6">
      <h2 className="font-semibold text-[15px] tracking-tight mb-4">Recent transactions</h2>
      {transactions.length === 0 ? (
        <p className="text-muted-foreground text-sm">No transactions yet.</p>
      ) : (
        <div className="space-y-0.5">
          {transactions.slice(0, 20).map((t) => (
            <TransactionRow
              key={t.id}
              transaction={t}
              categories={categories}
              onCategoryChange={onCategoryChange}
            />
          ))}
        </div>
      )}
    </Card>
  );
}

function TransactionRow({
  transaction: t,
  categories,
  onCategoryChange,
}: {
  transaction: Transaction;
  categories: Category[];
  onCategoryChange: (transactionId: string, categoryId: string) => void;
}) {
  const [saving, setSaving] = useState(false);
  const isIncome = t.amount < 0;

  async function handleChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const categoryId = e.target.value;
    if (!categoryId) return;
    setSaving(true);
    try {
      await api.transactions.updateCategory(t.id, categoryId);
      onCategoryChange(t.id, categoryId);
    } catch (err) {
      console.error(err);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="flex items-center gap-3 px-2 py-2.5 rounded-md hover:bg-secondary/50 transition-colors">
      <div
        className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 ${
          isIncome ? "bg-primary/10" : "bg-secondary"
        }`}
      >
        {isIncome ? (
          <ArrowDownLeft className="w-3.5 h-3.5 text-primary" />
        ) : (
          <ArrowUpRight className="w-3.5 h-3.5 text-muted-foreground" />
        )}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium truncate">{t.merchant_name ?? "Unknown"}</p>
        <p className="text-[11px] text-muted-foreground">{t.date}</p>
      </div>
      <select
        value={t.category_id ?? ""}
        onChange={handleChange}
        disabled={saving}
        className="text-xs bg-transparent border border-border rounded-md px-2 py-1 text-muted-foreground hover:text-foreground focus:outline-none focus:ring-2 focus:ring-ring/50 disabled:opacity-50 shrink-0"
      >
        <option value="" disabled>
          Uncategorized
        </option>
        {categories.map((c) => (
          <option key={c.id} value={c.id} className="bg-card text-foreground">
            {c.name}
          </option>
        ))}
      </select>
      <p
        className={`text-sm font-semibold font-mono shrink-0 w-20 text-right ${
          isIncome ? "text-primary" : "text-foreground"
        }`}
      >
        {isIncome ? "+" : "-"}
        {Math.abs(t.amount).toLocaleString("en-US", {
          style: "currency",
          currency: "USD",
        })}
      </p>
    </div>
  );
}
