"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowDownLeft, ArrowUpRight, Wallet } from "lucide-react";
import { api, Account, Transaction } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Sidebar } from "@/components/ui/Sidebar";

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
  const [plaidLinked, setPlaidLinked] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.auth.me()
      .then(setUser)
      .catch(() => router.push("/login"));
  }, [router]);

  useEffect(() => {
    if (!user) return;
    Promise.all([api.plaid.getAccounts(), api.plaid.getTransactions()])
      .then(([accts, txns]) => {
        setAccounts(accts);
        setTransactions(txns);
        setPlaidLinked(accts.length > 0);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [user]);

  async function handleLogout() {
    await api.auth.logout();
    router.push("/login");
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
      <Sidebar userEmail={user.email} accounts={accounts} onLogout={handleLogout} />

      <main className="flex-1 overflow-y-auto flex flex-col min-w-0">
        <header
          className="sticky top-0 z-10 border-b border-border px-8 py-4 flex-shrink-0"
          style={{ background: "rgba(7,16,31,0.85)", backdropFilter: "blur(12px)" }}
        >
          <h1 className="text-[18px] font-semibold tracking-tight">Dashboard</h1>
          <p className="text-xs text-muted-foreground mt-0.5">{today} · Your financial snapshot</p>
        </header>

        <div className="px-8 py-6 space-y-5 flex-1">
          <div
            className="rounded-2xl p-5 relative overflow-hidden"
            style={{ background: "linear-gradient(135deg, #10d98c 0%, #059669 100%)" }}
          >
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
                <div className="text-xs font-semibold" style={{ color: "rgba(7,16,31,0.7)" }}>
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
            <Card className="p-6">
              <h2 className="font-semibold text-[15px] tracking-tight mb-4">Recent transactions</h2>
              {transactions.length === 0 ? (
                <p className="text-muted-foreground text-sm">No transactions yet.</p>
              ) : (
                <div className="space-y-0.5">
                  {transactions.slice(0, 20).map((t) => {
                    const isIncome = t.amount < 0;
                    return (
                      <div
                        key={t.id}
                        className="flex items-center gap-3 px-2 py-2.5 rounded-md hover:bg-secondary/50 transition-colors"
                      >
                        <div
                          className={`w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 ${
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
                          <p className="text-sm font-medium truncate">
                            {t.merchant_name ?? "Unknown"}
                          </p>
                          <p className="text-[11px] text-muted-foreground">{t.date}</p>
                        </div>
                        <p
                          className={`text-sm font-semibold font-mono flex-shrink-0 ${
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
                  })}
                </div>
              )}
            </Card>
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
