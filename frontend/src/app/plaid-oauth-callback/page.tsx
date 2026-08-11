"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { loadPlaidScript, consumeStoredLinkToken } from "@/lib/plaidLink";

// Real banks that require Plaid's OAuth flow send the user here after they
// log in on the bank's own site. Link has to be re-opened with the same
// link_token it was started with (saved in localStorage before the redirect)
// plus this page's own URL, so it can pick the flow back up.
export default function PlaidOAuthCallbackPage() {
  const router = useRouter();
  const [error, setError] = useState("");
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return;
    started.current = true;

    const linkToken = consumeStoredLinkToken();
    if (!linkToken) {
      router.replace("/dashboard");
      return;
    }

    loadPlaidScript()
      .then(() => {
        // @ts-expect-error Plaid is loaded dynamically
        const handler = window.Plaid.create({
          token: linkToken,
          receivedRedirectUri: window.location.href,
          onSuccess: async (public_token: string) => {
            try {
              await api.plaid.exchangeToken(public_token);
            } catch (err) {
              console.error(err);
            } finally {
              router.replace("/dashboard");
            }
          },
          onExit: () => router.replace("/dashboard"),
        });
        handler.open();
      })
      .catch(() => setError("Failed to resume bank connection."));
  }, [router]);

  return (
    <div className="min-h-screen flex items-center justify-center">
      <p className="text-muted-foreground">{error || "Finishing bank connection…"}</p>
    </div>
  );
}
