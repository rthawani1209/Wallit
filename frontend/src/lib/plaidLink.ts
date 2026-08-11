// Shared between the "Connect bank account" button and the OAuth resume page:
// real institutions can redirect the user away to their bank's login and back,
// so the link_token has to survive that round trip via localStorage — Plaid
// requires resuming with the *same* token rather than creating a new one.
const PLAID_SCRIPT_SRC = "https://cdn.plaid.com/link/v2/stable/link-initialize.js";
const LINK_TOKEN_STORAGE_KEY = "plaid_link_token";

export function loadPlaidScript(): Promise<void> {
  return new Promise((resolve, reject) => {
    // @ts-expect-error Plaid is loaded dynamically onto window
    if (window.Plaid) {
      resolve();
      return;
    }
    const script = document.createElement("script");
    script.src = PLAID_SCRIPT_SRC;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Failed to load Plaid"));
    document.head.appendChild(script);
  });
}

export function storeLinkToken(token: string) {
  window.localStorage.setItem(LINK_TOKEN_STORAGE_KEY, token);
}

export function consumeStoredLinkToken(): string | null {
  const token = window.localStorage.getItem(LINK_TOKEN_STORAGE_KEY);
  window.localStorage.removeItem(LINK_TOKEN_STORAGE_KEY);
  return token;
}
