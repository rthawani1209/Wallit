"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { CalendarDays, LayoutDashboard, LogOut, RefreshCw, Repeat, Wallet } from "lucide-react";
import type { Account } from "@/lib/api";

interface SidebarProps {
  userEmail: string;
  accounts: Account[];
  onLogout: () => void;
  isOpen: boolean;
  onClose: () => void;
  onResync: () => void;
  syncing: boolean;
  lastSyncedLabel: string | null;
}

const navItems = [
  { icon: LayoutDashboard, label: "Dashboard", href: "/dashboard" },
  { icon: CalendarDays, label: "Calendar", href: "/calendar" },
  { icon: Repeat, label: "Subscriptions", href: "/subscriptions" },
];

const GRID_BACKGROUND = {
  backgroundImage:
    "linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px)",
  backgroundSize: "32px 32px",
};

function fmt(val: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(val);
}

function initials(email: string) {
  return email.slice(0, 2).toUpperCase();
}

export function Sidebar({
  userEmail,
  accounts,
  onLogout,
  isOpen,
  onClose,
  onResync,
  syncing,
  lastSyncedLabel,
}: SidebarProps) {
  const pathname = usePathname();

  return (
    <>
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 md:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}
      <aside
        className={`fixed md:static inset-y-0 left-0 z-50 w-[220px] flex-shrink-0 flex flex-col bg-sidebar border-r border-border transition-transform duration-200 md:translate-x-0 relative overflow-hidden ${
          isOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
      <div className="absolute inset-0 pointer-events-none" style={GRID_BACKGROUND} />
      <div
        className="absolute -top-20 -left-20 w-64 h-64 rounded-full opacity-[0.12] blur-3xl pointer-events-none"
        style={{ background: "radial-gradient(circle, #10d98c, transparent 70%)" }}
      />

      <div className="relative px-5 py-5 border-b border-border">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl bg-primary flex items-center justify-center shadow-[0_0_20px_rgba(16,217,140,0.45)]">
            <Wallet className="w-4.5 h-4.5 text-primary-foreground" />
          </div>
          <span
            className="font-bold text-lg tracking-tight bg-clip-text text-transparent"
            style={{ backgroundImage: "linear-gradient(135deg, #ffffff 30%, #7de8c4 100%)" }}
          >
            Wallit
          </span>
        </div>
      </div>

      <nav className="relative flex-1 px-3 pt-4 pb-2 overflow-y-auto">
        <p className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
          Workspace
        </p>
        <div className="space-y-0.5">
          {navItems.map(({ icon: Icon, label, href }) => {
            const active = pathname === href;
            return (
              <Link
                key={label}
                href={href}
                onClick={onClose}
                className={`relative w-full flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors ${
                  active
                    ? "bg-primary/10 text-primary shadow-[0_0_16px_-4px_rgba(16,217,140,0.4)]"
                    : "text-muted-foreground hover:text-sidebar-foreground hover:bg-white/[0.03]"
                }`}
              >
                {active && (
                  <span className="absolute left-0 top-1.5 bottom-1.5 w-[3px] rounded-full bg-primary shadow-[0_0_8px_rgba(16,217,140,0.8)]" />
                )}
                <Icon className="w-4 h-4 flex-shrink-0" />
                {label}
              </Link>
            );
          })}
        </div>

        <p className="px-3 pt-5 pb-2 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
          Accounts
        </p>
        {accounts.length === 0 ? (
          <p className="px-3 text-xs text-muted-foreground">No accounts linked</p>
        ) : (
          <div className="space-y-0.5">
            {accounts.map((a) => (
              <div
                key={a.id}
                className="flex items-center justify-between px-3 py-2 rounded-md"
              >
                <span className="flex items-center gap-2 flex-1 min-w-0 pr-2">
                  <span
                    className="w-1.5 h-1.5 rounded-full flex-shrink-0"
                    style={{ background: a.type === "credit" ? "#f43f5e" : "#10d98c" }}
                  />
                  <span className="text-xs text-muted-foreground truncate">{a.name}</span>
                </span>
                <span className="text-xs font-mono font-medium text-sidebar-foreground flex-shrink-0">
                  {a.current_balance !== null ? fmt(a.current_balance) : "—"}
                </span>
              </div>
            ))}
          </div>
        )}

        {accounts.length > 0 && (
          <div className="mt-6 mx-3 rounded-xl border border-white/[0.06] bg-white/[0.02] p-3.5">
            <div className="flex items-center justify-between mb-1">
              <span className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
                Sync
              </span>
              <span className="relative flex w-1.5 h-1.5">
                {!syncing && (
                  <span
                    className="absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"
                    style={{ animation: "auth-glow-pulse 2.5s ease-in-out infinite" }}
                  />
                )}
                <span className="relative inline-flex rounded-full w-1.5 h-1.5 bg-primary" />
              </span>
            </div>
            <p className="text-xs text-muted-foreground mb-3">
              {syncing ? "Syncing…" : lastSyncedLabel ? `Synced ${lastSyncedLabel}` : "Not synced yet"}
            </p>
            <button
              onClick={onResync}
              disabled={syncing}
              className="w-full flex items-center justify-center gap-1.5 rounded-md border border-border bg-secondary px-2.5 py-1.5 text-xs font-medium text-foreground hover:bg-secondary/80 transition-colors disabled:opacity-50 disabled:pointer-events-none"
            >
              <RefreshCw className={`w-3 h-3 ${syncing ? "animate-spin" : ""}`} />
              {syncing ? "Syncing" : "Resync accounts"}
            </button>
          </div>
        )}
      </nav>

      <div className="relative px-3 py-3 border-t border-border">
        <div className="flex items-center gap-3 px-3 py-2.5 rounded-md">
          <div className="w-7 h-7 rounded-full bg-primary flex items-center justify-center text-[11px] font-bold text-primary-foreground flex-shrink-0 shadow-[0_0_14px_rgba(16,217,140,0.5)]">
            {initials(userEmail)}
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-[13px] font-medium truncate text-sidebar-foreground">
              {userEmail}
            </div>
          </div>
          <button
            onClick={onLogout}
            aria-label="Log out"
            className="text-muted-foreground hover:text-sidebar-foreground transition-colors flex-shrink-0"
          >
            <LogOut className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
      </aside>
    </>
  );
}
