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
    signup: (email: string, password: string) =>
      request<{ id: string; email: string }>("/api/v1/auth/signup", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      }),

    login: (email: string, password: string) =>
      request<{ id: string; email: string }>("/api/v1/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      }),

    logout: () => request<void>("/api/v1/auth/logout", { method: "POST" }),

    me: () => request<{ id: string; email: string }>("/api/v1/auth/me"),
  },

  plaid: {
    createLinkToken: () =>
      request<{ link_token: string }>("/api/v1/plaid/link-token", { method: "POST" }),

    exchangeToken: (public_token: string) =>
      request<{ message: string }>("/api/v1/plaid/exchange-token", {
        method: "POST",
        body: JSON.stringify({ public_token }),
      }),

    getAccounts: () => request<Account[]>("/api/v1/plaid/accounts"),
    getTransactions: () => request<Transaction[]>("/api/v1/plaid/transactions"),
  },
};

export interface Account {
  id: string;
  plaid_account_id: string;
  name: string;
  type: string;
  current_balance: number | null;
}

export interface Transaction {
  id: string;
  amount: number;
  merchant_name: string | null;
  date: string;
  is_subscription: boolean;
  is_anomaly: boolean;
}
