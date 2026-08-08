"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Menu, Repeat, TrendingUp, Wallet as WalletIcon } from "lucide-react";
import { api, Account, Subscription, User } from "@/lib/api";
import { Card } from "@/components/ui/Card";
import { Sidebar } from "@/components/ui/Sidebar";
import { SubscriptionCard } from "@/components/subscriptions/SubscriptionCard";

const ANNUAL_MULTIPLIER: Record<string, number> = {
  weekly: 52,
  monthly: 12,
  quarterly: 4,
  annual: 1,
};

function fmt(val: number) {
  return val.toLocaleString("en-US", { style: "currency", currency: "USD" });
}

export default function SubscriptionsPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
  const [loading, setLoading] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [lastSyncedLabel, setLastSyncedLabel] = useState<string | null>(null);

  useEffect(() => {
    api.auth.me().then(setUser).catch(() => router.push("/login"));
  }, [router]);

  useEffect(() => {
    if (!user) return;
    Promise.all([api.accounts.getAll(), api.subscriptions.getAll()])
      .then(([accts, subs]) => {
        setAccounts(accts);
        setSubscriptions(subs);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [user]);

  async function handleLogout() {
    await api.auth.logout();
    router.push("/login");
  }

  async function handleResync() {
    setSyncing(true);
    try {
      await api.plaid.resync();
      const [accts, subs] = await Promise.all([api.accounts.getAll(), api.subscriptions.getAll()]);
      setAccounts(accts);
      setSubscriptions(subs);
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

  const annualTotal = subscriptions.reduce(
    (sum, s) => sum + s.amount * (ANNUAL_MULTIPLIER[s.billing_interval] ?? 12),
    0
  );
  const monthlyTotal = annualTotal / 12;

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
          style={{ background: "radial-gradient(circle, #6366f1, transparent 70%)" }}
        />

        <header
          className="sticky top-0 z-10 border-b border-border px-4 md:px-8 py-4 shrink-0 flex items-center gap-3"
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
            <h1 className="text-[18px] font-semibold tracking-tight">Subscriptions</h1>
            <p className="text-xs text-muted-foreground mt-0.5">
              Recurring charges detected automatically from your linked accounts
            </p>
          </div>
        </header>

        <div className="relative px-4 md:px-8 py-6 space-y-5 flex-1">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
            <Card className="p-5">
              <div className="flex items-center justify-between mb-2">
                <span className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
                  Monthly Total
                </span>
                <WalletIcon className="w-4 h-4 text-primary" />
              </div>
              <p className="text-2xl font-bold font-mono">{fmt(monthlyTotal)}</p>
            </Card>
            <Card className="p-5">
              <div className="flex items-center justify-between mb-2">
                <span className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
                  Annual Total
                </span>
                <TrendingUp className="w-4 h-4 text-primary" />
              </div>
              <p className="text-2xl font-bold font-mono">{fmt(annualTotal)}</p>
            </Card>
            <Card className="p-5">
              <div className="flex items-center justify-between mb-2">
                <span className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
                  Active
                </span>
                <Repeat className="w-4 h-4 text-primary" />
              </div>
              <p className="text-2xl font-bold font-mono">{subscriptions.length}</p>
            </Card>
          </div>

          {subscriptions.length === 0 ? (
            <Card className="p-10 text-center">
              <Repeat className="w-8 h-8 text-muted-foreground mx-auto mb-3" />
              <p className="text-foreground font-medium mb-1">No subscriptions detected yet</p>
              <p className="text-sm text-muted-foreground max-w-sm mx-auto">
                Once a merchant charges you at a consistent amount two or more times, it shows up
                here automatically — no need to add anything manually.
              </p>
            </Card>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {subscriptions.map((sub) => (
                <SubscriptionCard key={sub.id} sub={sub} />
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
