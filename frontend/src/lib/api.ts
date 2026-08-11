// Explicit NEXT_PUBLIC_API_URL always wins. If it's not set at all, use
// Next.js's own automatic NODE_ENV (never manually configured, so it can't be
// forgotten/left stale) rather than defaulting to localhost unconditionally —
// a production build with no override should proxy through its own domain
// (next.config.ts rewrites), not try to reach someone's laptop.
const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? (process.env.NODE_ENV === "production" ? "" : "http://localhost:8000");

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    credentials: "include", // send cookies (our JWT) with every request
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(error.detail || "Request failed");
  }

  return res.json();
}

export const api = {
  auth: {
    signup: (fields: {
      email: string;
      password: string;
      first_name: string;
      last_name: string;
      date_of_birth: string; // YYYY-MM-DD
    }) =>
      request<User>("/api/v1/auth/signup", {
        method: "POST",
        body: JSON.stringify(fields),
      }),

    login: (email: string, password: string) =>
      request<User>("/api/v1/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      }),

    logout: () => request<void>("/api/v1/auth/logout", { method: "POST" }),

    me: () => request<User>("/api/v1/auth/me"),
  },

  plaid: {
    createLinkToken: () =>
      request<{ link_token: string }>("/api/v1/plaid/link-token", { method: "POST" }),

    exchangeToken: (public_token: string) =>
      request<{ message: string }>("/api/v1/plaid/exchange-token", {
        method: "POST",
        body: JSON.stringify({ public_token }),
      }),

    resync: () =>
      request<{ message: string; transactions_touched: number }>("/api/v1/plaid/resync", {
        method: "POST",
      }),
  },

  accounts: {
    getAll: () => request<Account[]>("/api/v1/accounts"),
  },

  transactions: {
    getAll: () => request<Transaction[]>("/api/v1/transactions"),

    updateCategory: (id: string, category_id: string | null) =>
      request<Transaction>(`/api/v1/transactions/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ category_id }),
      }),

    getSummary: (range?: DateRange) => {
      const params = new URLSearchParams();
      if (range) {
        params.set("start_date", range.startDate);
        params.set("end_date", range.endDate);
      }
      const qs = params.toString();
      return request<CategorySpend[]>(`/api/v1/transactions/summary${qs ? `?${qs}` : ""}`);
    },

    getCashFlow: (months = 7) =>
      request<CashFlowMonth[]>(`/api/v1/transactions/cashflow?months=${months}`),

    getUpcomingBills: () => request<UpcomingBill[]>("/api/v1/transactions/upcoming-bills"),

    getAnomalies: () => request<Anomaly[]>("/api/v1/transactions/anomalies"),
  },

  subscriptions: {
    getAll: (discretionaryOnly = false) =>
      request<Subscription[]>(
        `/api/v1/subscriptions${discretionaryOnly ? "?discretionary_only=true" : ""}`
      ),

    getCalendar: (month: string) =>
      request<CalendarEvent[]>(`/api/v1/subscriptions/calendar?month=${month}`),
  },

  budgets: {
    getProgress: () => request<BudgetProgress[]>("/api/v1/budgets/progress"),

    set: (categoryId: string, limit: number) =>
      request<BudgetProgress>(`/api/v1/budgets/${categoryId}`, {
        method: "PUT",
        body: JSON.stringify({ limit }),
      }),
  },

  categories: {
    getAll: () => request<Category[]>("/api/v1/categories"),
  },

  plans: {
    getAll: () => request<Plan[]>("/api/v1/plans"),

    archive: (id: string) =>
      request<Plan>(`/api/v1/plans/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ is_active: false }),
      }),
  },

  chat: {
    send: (messages: ChatMessage[]) =>
      request<{ message: string }>("/api/v1/chat", {
        method: "POST",
        body: JSON.stringify({ messages }),
      }),
  },

  simulate: (percentChange: number, categoryId?: string, range?: DateRange) => {
    const params = new URLSearchParams({ percent_change: String(percentChange) });
    if (categoryId) params.set("category_id", categoryId);
    if (range) {
      params.set("start_date", range.startDate);
      params.set("end_date", range.endDate);
    }
    return request<SimulateResult>(`/api/v1/simulate?${params.toString()}`);
  },
};

export interface User {
  id: string;
  email: string;
  first_name: string | null;
  last_name: string | null;
}

export interface Account {
  id: string;
  name: string;
  type: string;
  current_balance: number | null;
}

export interface Transaction {
  id: string;
  amount: number;
  merchant_name: string | null;
  date: string;
  category_id: string | null;
  is_subscription: boolean;
  is_anomaly: boolean;
}

export interface Category {
  id: string;
  name: string;
}

export interface CategorySpend {
  category_id: string | null;
  category_name: string;
  total: number;
}

export interface SimulateResult {
  current_balance: number;
  actual_spend: number;
  projected_spend: number;
  projected_balance: number;
}

export interface DateRange {
  startDate: string; // YYYY-MM-DD
  endDate: string; // YYYY-MM-DD
}

export interface CashFlowMonth {
  month: string; // "2026-02"
  label: string; // "Feb"
  income: number;
  expenses: number;
}

export interface BudgetProgress {
  category_id: string;
  category_name: string;
  limit: number;
  spent: number;
  is_custom: boolean;
}

export interface UpcomingBill {
  merchant_name: string;
  amount: number;
  next_due_date: string; // YYYY-MM-DD
}

export interface Subscription {
  id: string;
  merchant_name: string;
  amount: number;
  billing_interval: string; // "weekly" | "monthly" | "quarterly" | "annual"
  next_estimated_date: string | null;
  category_name: string | null;
  cheaper_alternative: string | null;
  is_active: boolean;
}

export interface CalendarEvent {
  date: string; // YYYY-MM-DD
  merchant_name: string;
  amount: number;
  category_name: string | null;
  billing_interval: string;
}

export interface Plan {
  id: string;
  type: string;
  name: string;
  target_amount: number;
  target_date: string | null; // YYYY-MM-DD
  location: string | null;
  monthly_contribution: number | null;
  is_active: boolean;
  created_at: string;
  saved_amount: number;
  progress_pct: number;
  is_achieved: boolean;
  projected_completion_date: string | null;
  on_track: boolean | null;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface Anomaly {
  id: string;
  merchant_name: string | null;
  amount: number;
  date: string;
  category_name: string | null;
  anomaly_reason: string | null;
}
