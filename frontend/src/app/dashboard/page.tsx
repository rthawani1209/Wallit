"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Menu, Wallet } from "lucide-react";
import { api, Account, Anomaly, BudgetProgress as BudgetProgressData, CashFlowMonth, Category, CategorySpend, Plan, Transaction, UpcomingBill } from "@/lib/api";
import { getDateRange, periodLabel as formatPeriodLabel, Period } from "@/lib/dateRange";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Sidebar } from "@/components/ui/Sidebar";
import { TransactionList } from "@/components/dashboard/TransactionList";
import { SpendChart } from "@/components/dashboard/SpendChart";
import { CashFlowChart } from "@/components/dashboard/CashFlowChart";
import { BudgetProgress } from "@/components/dashboard/BudgetProgress";
import { SavingsGoals } from "@/components/dashboard/SavingsGoals";
import { UpcomingBills } from "@/components/dashboard/UpcomingBills";
import { AnomaliesCard } from "@/components/dashboard/AnomaliesCard";
import { WhatIfSimulator } from "@/components/dashboard/WhatIfSimulator";
import { PeriodSelector } from "@/components/dashboard/PeriodSelector";

const today = new Date().toLocaleDateString("en-US", {
  weekday: "long",
  month: "long",
  day: "numeric",
});

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<{ id: string; email: string } | null>(null);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [spendSummary, setSpendSummary] = useState<CategorySpend[]>([]);
  const [cashFlow, setCashFlow] = useState<CashFlowMonth[]>([]);
  const [budgetProgress, setBudgetProgress] = useState<BudgetProgressData[]>([]);
  const [upcomingBills, setUpcomingBills] = useState<UpcomingBill[]>([]);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [anomalies, setAnomalies] = useState<Anomaly[]>([]);
  const [plaidLinked, setPlaidLinked] = useState(false);
  const [loading, setLoading] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [lastSyncedLabel, setLastSyncedLabel] = useState<string | null>(null);
  const [period, setPeriod] = useState<Period>("this_month");
  const [customMonth, setCustomMonth] = useState(new Date().toISOString().slice(0, 7));

  const dateRange = useMemo(
    () => getDateRange(period, customMonth),
    [period, customMonth]
  );
  const currentPeriodLabel = useMemo(
    () => formatPeriodLabel(period, customMonth),
    [period, customMonth]
  );

  useEffect(() => {
    api.auth.me()
      .then(setUser)
      .catch(() => router.push("/login"));
  }, [router]);

  useEffect(() => {
    if (!user) return;
    Promise.all([
      api.accounts.getAll(),
      api.transactions.getAll(),
      api.categories.getAll(),
    ])
      .then(([accts, txns, cats]) => {
        setAccounts(accts);
        setTransactions(txns);
        setCategories(cats);
        setPlaidLinked(accts.length > 0);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [user]);

  useEffect(() => {
    if (!user || !plaidLinked) return;
    api.transactions.getSummary(dateRange).then(setSpendSummary).catch(() => {});
  }, [user, plaidLinked, dateRange]);

  useEffect(() => {
    if (!user || !plaidLinked) return;
    api.transactions.getCashFlow().then(setCashFlow).catch(() => {});
  }, [user, plaidLinked]);

  useEffect(() => {
    if (!user || !plaidLinked) return;
    api.budgets.getProgress().then(setBudgetProgress).catch(() => {});
  }, [user, plaidLinked]);

  useEffect(() => {
    if (!user || !plaidLinked) return;
    api.transactions.getUpcomingBills().then(setUpcomingBills).catch(() => {});
  }, [user, plaidLinked]);

  useEffect(() => {
    if (!user || !plaidLinked) return;
    api.transactions.getAnomalies().then(setAnomalies).catch(() => {});
  }, [user, plaidLinked]);

  useEffect(() => {
    if (!user || !plaidLinked) return;
    api.plans.getAll().then(setPlans).catch(() => {});
  }, [user, plaidLinked]);

  async function handleArchivePlan(id: string) {
    const updated = await api.plans.archive(id);
    setPlans((prev) => prev.filter((p) => p.id !== updated.id));
  }

  async function handleSetBudget(categoryId: string, limit: number) {
    const updated = await api.budgets.set(categoryId, limit);
    setBudgetProgress((prev) => {
      const exists = prev.some((b) => b.category_id === categoryId);
      return exists
        ? prev.map((b) => (b.category_id === categoryId ? updated : b))
        : [...prev, updated];
    });
  }

  function handleCategoryChange(transactionId: string, categoryId: string) {
    setTransactions((prev) =>
      prev.map((t) => (t.id === transactionId ? { ...t, category_id: categoryId } : t))
    );
    // Recategorizing shifts the spend breakdown, so refresh the chart from the server
    // rather than duplicating the aggregation logic on the client.
    api.transactions.getSummary(dateRange).then(setSpendSummary).catch(() => {});
  }

  async function handleLogout() {
    await api.auth.logout();
    router.push("/login");
  }

  async function handleResync() {
    setSyncing(true);
    try {
      await api.plaid.resync();
      const [accts, txns] = await Promise.all([api.accounts.getAll(), api.transactions.getAll()]);
      setAccounts(accts);
      setTransactions(txns);
      await Promise.all([
        api.transactions.getSummary(dateRange).then(setSpendSummary),
        api.transactions.getCashFlow().then(setCashFlow),
        api.budgets.getProgress().then(setBudgetProgress),
        api.transactions.getUpcomingBills().then(setUpcomingBills),
        api.transactions.getAnomalies().then(setAnomalies),
        api.plans.getAll().then(setPlans),
      ]);
      setLastSyncedLabel("just now");
    } catch (err) {
      console.error(err);
    } finally {
      setSyncing(false);
    }
  }

  if (!user || loading) {
    return (
      <main className="min-h-screen flex items-center justify-center bg-background">
        <p className="text-muted-foreground text-sm">Loading…</p>
      </main>
    );
  }

  const totalBalance = accounts.reduce((sum, a) => sum + (a.current_balance ?? 0), 0);

  return (
    <div className="flex h-screen bg-background text-foreground overflow-hidden">
      <Sidebar
        userEmail={user.email}
        accounts={accounts}
        onLogout={handleLogout}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        onResync={handleResync}
        syncing={syncing}
        lastSyncedLabel={lastSyncedLabel}
      />

      <main className="flex-1 overflow-y-auto flex flex-col min-w-0 relative">
        <div
          className="fixed inset-0 pointer-events-none opacity-[0.4]"
          style={{
            backgroundImage:
              "linear-gradient(rgba(255,255,255,0.025) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.025) 1px, transparent 1px)",
            backgroundSize: "48px 48px",
          }}
        />
        <div
          className="fixed top-0 right-0 w-[36rem] h-[36rem] rounded-full opacity-[0.06] blur-3xl pointer-events-none"
          style={{ background: "radial-gradient(circle, #10d98c, transparent 70%)" }}
        />

        <header
          className="sticky top-0 z-10 border-b border-border px-4 md:px-8 py-4 flex-shrink-0 flex items-center gap-3"
          style={{ background: "rgba(7,16,31,0.85)", backdropFilter: "blur(12px)" }}
        >
          <button
            onClick={() => setSidebarOpen(true)}
            aria-label="Open menu"
            className="md:hidden text-muted-foreground hover:text-foreground transition-colors"
          >
            <Menu className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-[18px] font-semibold tracking-tight">Dashboard</h1>
            <p className="text-xs text-muted-foreground mt-0.5">{today} · Your financial snapshot</p>
          </div>
        </header>

        <div className="relative px-4 md:px-8 py-6 space-y-5 flex-1">
          <div
            className="rounded-2xl p-5 relative overflow-hidden shadow-[0_0_40px_-12px_rgba(16,217,140,0.5)]"
            style={{ background: "linear-gradient(135deg, #10d98c 0%, #059669 100%)" }}
          >
            <div
              className="absolute inset-0 opacity-[0.15]"
              style={{
                backgroundImage:
                  "linear-gradient(rgba(255,255,255,0.4) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.4) 1px, transparent 1px)",
                backgroundSize: "20px 20px",
              }}
            />
            <div className="absolute -right-4 -top-4 w-24 h-24 rounded-full opacity-10 bg-white" />
            <div className="relative">
              <div className="flex items-center justify-between mb-3">
                <span
                  className="text-[10px] font-semibold uppercase tracking-widest"
                  style={{ color: "rgba(7,16,31,0.65)" }}
                >
                  Total Balance
                </span>
                <Wallet className="w-4 h-4" style={{ color: "rgba(7,16,31,0.5)" }} />
              </div>
              <div
                className="text-3xl font-bold tracking-tight mb-2 font-mono"
                style={{ color: "#07101f" }}
              >
                {totalBalance.toLocaleString("en-US", {
                  style: "currency",
                  currency: "USD",
                })}
              </div>
              {accounts.length > 0 && (
                <div
                  className="flex items-center gap-1.5 text-xs font-semibold"
                  style={{ color: "rgba(7,16,31,0.7)" }}
                >
                  <span className="relative flex w-1.5 h-1.5">
                    <span
                      className="absolute inline-flex h-full w-full rounded-full opacity-75"
                      style={{ background: "#07101f", animation: "auth-glow-pulse 2s ease-in-out infinite" }}
                    />
                    <span className="relative inline-flex rounded-full w-1.5 h-1.5" style={{ background: "#07101f" }} />
                  </span>
                  {accounts.length} account{accounts.length !== 1 ? "s" : ""} connected
                </div>
              )}
            </div>
          </div>

          {!plaidLinked ? (
            <Card className="p-6 text-center">
              <p className="text-foreground mb-4">Connect a bank account to get started.</p>
              <PlaidConnectButton onSuccess={() => window.location.reload()} />
            </Card>
          ) : (
            <>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Showing</span>
                <PeriodSelector
                  period={period}
                  customMonth={customMonth}
                  onPeriodChange={setPeriod}
                  onCustomMonthChange={setCustomMonth}
                />
              </div>

              <AnomaliesCard data={anomalies} />

              <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                <div className="md:col-span-2">
                  <CashFlowChart data={cashFlow} />
                </div>
                <SpendChart data={spendSummary} periodLabel={currentPeriodLabel} />
                <div className="md:col-span-2">
                  <TransactionList
                    transactions={transactions}
                    categories={categories}
                    onCategoryChange={handleCategoryChange}
                  />
                </div>
                <div className="space-y-5">
                  <BudgetProgress data={budgetProgress} onSetLimit={handleSetBudget} />
                  <SavingsGoals data={plans} onArchive={handleArchivePlan} />
                  <UpcomingBills data={upcomingBills} />
                </div>
                <div className="md:col-span-3">
                  <WhatIfSimulator
                    categories={categories}
                    dateRange={dateRange}
                    periodLabel={currentPeriodLabel}
                  />
                </div>
              </div>
            </>
          )}
        </div>
      </main>
    </div>
  );
}

function PlaidConnectButton({ onSuccess }: { onSuccess: () => void }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleClick() {
    setError("");
    setLoading(true);
    try {
      const { link_token } = await api.plaid.createLinkToken();

      // Dynamically load the Plaid Link script
      const script = document.createElement("script");
      script.src = "https://cdn.plaid.com/link/v2/stable/link-initialize.js";
      script.onload = () => {
        // @ts-expect-error Plaid is loaded dynamically
        const handler = window.Plaid.create({
          token: link_token,
          onSuccess: async (public_token: string) => {
            try {
              await api.plaid.exchangeToken(public_token);
              onSuccess();
            } catch (err) {
              console.error(err);
              setError(err instanceof Error ? err.message : "Failed to connect bank account");
              setLoading(false);
            }
          },
          onExit: () => setLoading(false),
        });
        handler.open();
      };
      document.head.appendChild(script);
    } catch (err) {
      console.error(err);
      setError(err instanceof Error ? err.message : "Failed to connect bank account");
      setLoading(false);
    }
  }

  return (
    <div>
      <Button onClick={handleClick} loading={loading} loadingText="Opening Plaid…">
        Connect bank account
      </Button>
      {error && <p className="text-destructive text-sm mt-3">{error}</p>}
    </div>
  );
}
