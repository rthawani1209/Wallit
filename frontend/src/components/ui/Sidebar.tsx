"use client";

import { LayoutDashboard, LogOut, Wallet } from "lucide-react";
import type { Account } from "@/lib/api";

interface SidebarProps {
  userEmail: string;
  accounts: Account[];
  onLogout: () => void;
}

const navItems = [{ icon: LayoutDashboard, label: "Dashboard" }];

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

export function Sidebar({ userEmail, accounts, onLogout }: SidebarProps) {
  return (
    <aside className="w-[220px] flex-shrink-0 flex flex-col bg-sidebar border-r border-border">
      <div className="px-5 py-5 border-b border-border">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-xl bg-primary flex items-center justify-center">
            <Wallet className="w-4 h-4 text-primary-foreground" />
          </div>
          <span className="font-semibold text-[15px] tracking-tight text-sidebar-foreground">
            Wallit
          </span>
        </div>
      </div>

      <nav className="flex-1 px-3 pt-4 pb-2 overflow-y-auto">
        <p className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
          Workspace
        </p>
        <div className="space-y-0.5">
          {navItems.map(({ icon: Icon, label }) => (
            <div
              key={label}
              className="w-full flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium bg-primary/10 text-primary"
            >
              <Icon className="w-4 h-4 flex-shrink-0" />
              {label}
            </div>
          ))}
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
                <span className="text-xs text-muted-foreground truncate flex-1 min-w-0 pr-2">
                  {a.name}
                </span>
                <span className="text-xs font-mono font-medium text-sidebar-foreground flex-shrink-0">
                  {a.current_balance !== null ? fmt(a.current_balance) : "—"}
                </span>
              </div>
            ))}
          </div>
        )}
      </nav>

      <div className="px-3 py-3 border-t border-border">
        <div className="flex items-center gap-3 px-3 py-2.5 rounded-md">
          <div className="w-7 h-7 rounded-full bg-primary flex items-center justify-center text-[11px] font-bold text-primary-foreground flex-shrink-0">
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
  );
}
