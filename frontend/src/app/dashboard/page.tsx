"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, Account, Transaction } from "@/lib/api";

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
      <main className="min-h-screen flex items-center justify-center bg-gray-50">
        <p className="text-gray-500">Loading…</p>
      </main>
    );
  }

  const totalBalance = accounts.reduce((sum, a) => sum + (a.current_balance ?? 0), 0);

  return (
    <main className="min-h-screen bg-gray-50">
      <nav className="bg-white border-b px-6 py-4 flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">Wallit</h1>
        <div className="flex items-center gap-4">
          <span className="text-sm text-gray-600">{user.email}</span>
          <button
            onClick={handleLogout}
            className="text-sm text-blue-600 hover:underline"
          >
            Log out
          </button>
        </div>
      </nav>

      <div className="max-w-4xl mx-auto px-6 py-8 space-y-6">
        {/* Balance card */}
        <div className="bg-white rounded-2xl shadow p-6">
          <p className="text-sm text-gray-500">Total balance</p>
          <p className="text-4xl font-bold text-gray-900 mt-1">
            ${totalBalance.toFixed(2)}
          </p>
          {accounts.length > 0 && (
            <p className="text-sm text-gray-500 mt-1">{accounts.length} account{accounts.length !== 1 ? "s" : ""} connected</p>
          )}
        </div>

        {/* Connect bank or show transactions */}
        {!plaidLinked ? (
          <div className="bg-white rounded-2xl shadow p-6 text-center">
            <p className="text-gray-700 mb-4">Connect a bank account to get started.</p>
            <PlaidConnectButton userId={user.id} onSuccess={() => window.location.reload()} />
          </div>
        ) : (
          <div className="bg-white rounded-2xl shadow p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Recent transactions</h2>
            {transactions.length === 0 ? (
              <p className="text-gray-500 text-sm">No transactions yet.</p>
            ) : (
              <ul className="divide-y">
                {transactions.slice(0, 20).map((t) => (
                  <li key={t.id} className="py-3 flex items-center justify-between">
                    <div>
                      <p className="font-medium text-gray-900">{t.merchant_name ?? "Unknown"}</p>
                      <p className="text-xs text-gray-500">{t.date}</p>
                    </div>
                    <p className={`font-semibold ${t.amount > 0 ? "text-red-600" : "text-green-600"}`}>
                      {t.amount > 0 ? "-" : "+"}${Math.abs(t.amount).toFixed(2)}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>
    </main>
  );
}

function PlaidConnectButton({ userId, onSuccess }: { userId: string; onSuccess: () => void }) {
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
    <button
      onClick={handleClick}
      disabled={loading}
      className="bg-blue-600 text-white rounded-lg px-6 py-2 font-medium hover:bg-blue-700 disabled:opacity-50"
    >
      {loading ? "Opening Plaid…" : "Connect bank account"}
    </button>
  );
}
