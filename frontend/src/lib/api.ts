const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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

    updateCategory: (id: string, category_id: string) =>
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
