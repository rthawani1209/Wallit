"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Menu, Send, Sparkles } from "lucide-react";
import { api, Account, ChatMessage, User } from "@/lib/api";
import { getStoredMessages, setStoredMessages } from "@/lib/chatStore";
import { Sidebar } from "@/components/ui/Sidebar";
import { MessageBubble } from "@/components/assistant/MessageBubble";

const SUGGESTIONS = [
  "How much did I spend on food this month?",
  "What subscriptions am I paying for?",
  "What bills are due this month?",
  "Find cheap places to eat near Austin, TX",
];

export default function AssistantPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [loadingUser, setLoadingUser] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [lastSyncedLabel, setLastSyncedLabel] = useState<string | null>(null);

  const [messages, setMessages] = useState<ChatMessage[]>(() => getStoredMessages());
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    api.auth.me().then(setUser).catch(() => router.push("/login"));
  }, [router]);

  useEffect(() => {
    if (!user) return;
    api.accounts.getAll().then(setAccounts).catch(() => {}).finally(() => setLoadingUser(false));
  }, [user]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  useEffect(() => {
    setStoredMessages(messages);
  }, [messages]);

  async function handleLogout() {
    await api.auth.logout();
    router.push("/login");
  }

  async function handleResync() {
    setSyncing(true);
    try {
      await api.plaid.resync();
      setAccounts(await api.accounts.getAll());
      setLastSyncedLabel("just now");
    } catch (err) {
      console.error(err);
    } finally {
      setSyncing(false);
    }
  }

  async function sendMessage(text: string) {
    const trimmed = text.trim();
    if (!trimmed || sending) return;

    const nextMessages = [...messages, { role: "user" as const, content: trimmed }];
    setMessages(nextMessages);
    setInput("");
    setError(null);
    setSending(true);
    if (textareaRef.current) textareaRef.current.style.height = "auto";

    try {
      const res = await api.chat.send(nextMessages);
      setMessages([...nextMessages, { role: "assistant", content: res.message }]);
    } catch (err) {
      console.error(err);
      setError("Couldn't reach the assistant. Check your connection and try again.");
    } finally {
      setSending(false);
    }
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    sendMessage(input);
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  }

  function handleInputChange(e: React.ChangeEvent<HTMLTextAreaElement>) {
    setInput(e.target.value);
    const el = e.target;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }

  if (!user || loadingUser) {
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

      <main className="flex-1 overflow-hidden flex flex-col min-w-0 relative">
        <div
          className="fixed inset-0 pointer-events-none opacity-[0.4]"
          style={{
            backgroundImage:
              "linear-gradient(rgba(255,255,255,0.025) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.025) 1px, transparent 1px)",
            backgroundSize: "48px 48px",
          }}
        />
        <div
          className="fixed top-0 right-0 w-[36rem] h-[36rem] rounded-full opacity-[0.08] blur-3xl pointer-events-none"
          style={{ background: "radial-gradient(circle, #10d98c, transparent 70%)" }}
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
            <h1 className="text-[18px] font-semibold tracking-tight">Assistant</h1>
            <p className="text-xs text-muted-foreground mt-0.5">
              Ask about your spending, bills, and subscriptions — or anything else.
            </p>
          </div>
        </header>

        <div className="relative flex-1 overflow-y-auto px-4 md:px-8 py-6">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center max-w-lg mx-auto">
              <div className="w-14 h-14 rounded-2xl bg-primary/10 border border-primary/25 flex items-center justify-center mb-4 shadow-[0_0_30px_-8px_rgba(16,217,140,0.6)]">
                <Sparkles className="w-6 h-6 text-primary" />
              </div>
              <h2 className="text-lg font-semibold mb-1.5">What can I help with?</h2>
              <p className="text-sm text-muted-foreground mb-6">
                I can see your real transactions, subscriptions, and bills — ask me anything about your money.
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full">
                {SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    onClick={() => sendMessage(s)}
                    className="text-left text-xs px-3.5 py-2.5 rounded-xl border border-white/[0.06] bg-white/[0.02] hover:bg-white/[0.05] hover:border-primary/30 transition-colors text-muted-foreground hover:text-foreground"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="max-w-3xl mx-auto space-y-4">
              {messages.map((m, i) => (
                <MessageBubble key={i} message={m} />
              ))}
              {sending && (
                <div className="flex gap-3 justify-start">
                  <div className="w-7 h-7 rounded-lg bg-primary/15 border border-primary/30 flex items-center justify-center flex-shrink-0">
                    <Sparkles className="w-3.5 h-3.5 text-primary" />
                  </div>
                  <div className="rounded-2xl rounded-bl-sm px-4 py-3 bg-white/[0.04] border border-white/[0.06] flex items-center gap-1">
                    {[0, 1, 2].map((i) => (
                      <span
                        key={i}
                        className="w-1.5 h-1.5 rounded-full bg-muted-foreground"
                        style={{ animation: `assistant-dot 1.2s ease-in-out ${i * 0.15}s infinite` }}
                      />
                    ))}
                  </div>
                </div>
              )}
              {error && (
                <div className="max-w-3xl mx-auto text-xs text-destructive bg-destructive/10 border border-destructive/25 rounded-lg px-3.5 py-2.5">
                  {error}
                </div>
              )}
              <div ref={bottomRef} />
            </div>
          )}
        </div>

        <div className="relative shrink-0 border-t border-border px-4 md:px-8 py-4" style={{ background: "rgba(7,16,31,0.85)", backdropFilter: "blur(12px)" }}>
          <form onSubmit={handleSubmit} className="max-w-3xl mx-auto flex items-end gap-2">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              placeholder="Message the assistant…"
              rows={1}
              className="flex-1 resize-none rounded-xl border border-border bg-secondary px-4 py-3 text-sm outline-none focus:border-primary/50 transition-colors placeholder:text-muted-foreground max-h-40"
            />
            <button
              type="submit"
              disabled={!input.trim() || sending}
              aria-label="Send message"
              className="w-11 h-11 shrink-0 rounded-xl bg-primary text-primary-foreground flex items-center justify-center transition-all hover:shadow-[0_0_20px_-4px_rgba(16,217,140,0.7)] disabled:opacity-40 disabled:pointer-events-none"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
        </div>
      </main>
    </div>
  );
}
