"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, Account, Transaction } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Nav } from "@/components/ui/Nav";

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
        <p className="text-muted text-sm">Loading…</p>
      </main>
    );
  }

  const totalBalance = accounts.reduce((sum, a) => sum + (a.current_balance ?? 0), 0);

  return (
    <main className="min-h-screen bg-background">
      <Nav userEmail={user.email} onLogout={handleLogout} />

      <div className="max-w-4xl mx-auto px-6 py-8 space-y-6">
        <Card className="p-6">
          <p className="text-sm text-muted">Total balance</p>
          <p className="text-4xl font-bold text-foreground mt-1 tabular-nums">
            ${totalBalance.toFixed(2)}
          </p>
          {accounts.length > 0 && (
            <p className="text-sm text-muted mt-1">
              {accounts.length} account{accounts.length !== 1 ? "s" : ""} connected
            </p>
          )}
        </Card>

        {!plaidLinked ? (
          <Card className="p-6 text-center">
            <p className="text-foreground mb-4">Connect a bank account to get started.</p>
            <PlaidConnectButton onSuccess={() => window.location.reload()} />
          </Card>
        ) : (
          <Card className="p-6">
            <h2 className="text-lg font-semibold text-foreground mb-4">Recent transactions</h2>
            {transactions.length === 0 ? (
              <p className="text-muted text-sm">No transactions yet.</p>
            ) : (
              <ul className="divide-y divide-border">
                {transactions.slice(0, 20).map((t) => (
                  <li key={t.id} className="py-3 flex items-center justify-between">
                    <div>
                      <p className="font-medium text-foreground">{t.merchant_name ?? "Unknown"}</p>
                      <p className="text-xs text-muted">{t.date}</p>
                    </div>
                    <p
                      className={`font-semibold tabular-nums ${
                        t.amount > 0 ? "text-danger" : "text-success"
                      }`}
                    >
                      {t.amount > 0 ? "-" : "+"}${Math.abs(t.amount).toFixed(2)}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        )}
      </div>
    </main>
  );
}

function PlaidConnectButton({ onSuccess }: { onSuccess: () => void }) {
  const [loading, setLoading] = useState(false);

  async function handleClick() {
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
            await api.plaid.exchangeToken(public_token);
            onSuccess();
          },
          onExit: () => setLoading(false),
        });
        handler.open();
      };
      document.head.appendChild(script);
    } catch (err) {
      console.error(err);
      setLoading(false);
    }
  }

  return (
    <Button onClick={handleClick} loading={loading} loadingText="Opening Plaid…">
      Connect bank account
    </Button>
  );
}
