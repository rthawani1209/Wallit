"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { CalendarDays, Menu, Receipt } from "lucide-react";
import { api, Account, CalendarEvent, User } from "@/lib/api";
import { Card } from "@/components/ui/Card";
import { Sidebar } from "@/components/ui/Sidebar";
import { CalendarGrid } from "@/components/calendar/CalendarGrid";

function fmt(val: number) {
  return val.toLocaleString("en-US", { style: "currency", currency: "USD" });
}

function fmtDay(iso: string) {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
  });
}

function monthKey(d: Date) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

export default function CalendarPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [lastSyncedLabel, setLastSyncedLabel] = useState<string | null>(null);
  const [monthStart, setMonthStart] = useState(() => {
    const now = new Date();
    return new Date(now.getFullYear(), now.getMonth(), 1);
  });
  const [selectedDate, setSelectedDate] = useState<string | null>(null);

  useEffect(() => {
    api.auth.me().then(setUser).catch(() => router.push("/login"));
  }, [router]);

  useEffect(() => {
    if (!user) return;
    api.accounts.getAll().then(setAccounts).catch(() => {}).finally(() => setLoading(false));
  }, [user]);

  useEffect(() => {
    if (!user) return;
    setSelectedDate(null);
    api.subscriptions.getCalendar(monthKey(monthStart)).then(setEvents).catch(() => {});
  }, [user, monthStart]);

  async function handleLogout() {
    await api.auth.logout();
    router.push("/login");
  }

  async function handleResync() {
    setSyncing(true);
    try {
      await api.plaid.resync();
      const [accts, evts] = await Promise.all([
        api.accounts.getAll(),
        api.subscriptions.getCalendar(monthKey(monthStart)),
      ]);
      setAccounts(accts);
      setEvents(evts);
      setLastSyncedLabel("just now");
    } catch (err) {
      console.error(err);
    } finally {
      setSyncing(false);
    }
  }

  const selectedEvents = useMemo(
    () => (selectedDate ? events.filter((e) => e.date === selectedDate) : []),
    [events, selectedDate]
  );
  const monthTotal = events.reduce((sum, e) => sum + e.amount, 0);

  if (!user || loading) {
    return (
      <main className="min-h-screen flex items-center justify-center bg-background">
        <p className="text-muted-foreground text-sm">Loading…</p>
      </main>
    );
  }

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
          style={{ background: "radial-gradient(circle, #8b5cf6, transparent 70%)" }}
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
            <h1 className="text-[18px] font-semibold tracking-tight">Calendar</h1>
            <p className="text-xs text-muted-foreground mt-0.5">
              Every upcoming bill and subscription charge, by date
            </p>
          </div>
        </header>

        <div className="relative px-4 md:px-8 py-6 space-y-5 flex-1">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
            <Card className="p-5">
              <div className="flex items-center justify-between mb-2">
                <span className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
                  Due This Month
                </span>
                <Receipt className="w-4 h-4 text-primary" />
              </div>
              <p className="text-2xl font-bold font-mono">{fmt(monthTotal)}</p>
            </Card>
            <Card className="p-5">
              <div className="flex items-center justify-between mb-2">
                <span className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
                  Charges
                </span>
                <CalendarDays className="w-4 h-4 text-primary" />
              </div>
              <p className="text-2xl font-bold font-mono">{events.length}</p>
            </Card>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
            <div className="lg:col-span-2">
              <CalendarGrid
                monthStart={monthStart}
                events={events}
                selectedDate={selectedDate}
                onSelectDate={setSelectedDate}
                onPrevMonth={() =>
                  setMonthStart((m) => new Date(m.getFullYear(), m.getMonth() - 1, 1))
                }
                onNextMonth={() =>
                  setMonthStart((m) => new Date(m.getFullYear(), m.getMonth() + 1, 1))
                }
              />
            </div>

            <Card className="p-5 h-fit lg:sticky lg:top-20">
              {selectedDate ? (
                <>
                  <h3 className="font-semibold text-sm mb-3">{fmtDay(selectedDate)}</h3>
                  <div className="space-y-3">
                    {selectedEvents.map((e, i) => (
                      <div key={i} className="flex items-start justify-between gap-3 pb-3 border-b border-border last:border-0 last:pb-0">
                        <div className="min-w-0">
                          <p className="text-sm font-medium truncate">{e.merchant_name}</p>
                          <p className="text-xs text-muted-foreground">
                            {e.category_name ?? "Uncategorized"} · {e.billing_interval}
                          </p>
                        </div>
                        <p className="text-sm font-mono font-semibold shrink-0">{fmt(e.amount)}</p>
                      </div>
                    ))}
                  </div>
                </>
              ) : (
                <div className="text-center py-6">
                  <CalendarDays className="w-6 h-6 text-muted-foreground mx-auto mb-2" />
                  <p className="text-sm text-muted-foreground">
                    Click a day with charges to see the details.
                  </p>
                </div>
              )}
            </Card>
          </div>
        </div>
      </main>
    </div>
  );
}
