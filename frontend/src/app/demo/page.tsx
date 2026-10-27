"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Check, Loader2, Wallet } from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/Button";

// Each line is something the backend really does when it builds a demo
// account (services/demo.py), paced so a visitor can read along.
const STEPS = [
  { label: "Creating a private sandbox account", detail: "no email, no bank, gone in 24h" },
  { label: "Generating 8 months of transactions", detail: "paychecks, rent, groceries, a few splurges" },
  { label: "Categorizing every transaction", detail: "Plaid category → keywords → catch-all" },
  { label: "Detecting subscriptions", detail: "stable amount + steady cadence" },
  { label: "Flagging unusual spending", detail: "mean + 2σ per category, $20 floor" },
];
const STEP_MS = 520;

type Status = "booting" | "error";

export default function DemoPage() {
  const router = useRouter();
  const [stepsShown, setStepsShown] = useState(1);
  const [status, setStatus] = useState<Status>("booting");
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  const [sessionReady, setSessionReady] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api.demo
      .start()
      .then(() => {
        if (!cancelled) setSessionReady(true);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Couldn't start the demo");
        setStatus("error");
      });
    return () => {
      cancelled = true;
    };
  }, [attempt]);

  useEffect(() => {
    if (status !== "booting") return;
    const timer = setInterval(() => {
      setStepsShown((n) => Math.min(n + 1, STEPS.length));
    }, STEP_MS);
    return () => clearInterval(timer);
  }, [status, attempt]);

  const finished = stepsShown === STEPS.length && sessionReady;

  useEffect(() => {
    if (!finished) return;
    const timer = setTimeout(() => router.replace("/dashboard"), STEP_MS);
    return () => clearTimeout(timer);
  }, [finished, router]);

  function retry() {
    setError("");
    setSessionReady(false);
    setStepsShown(1);
    setStatus("booting");
    setAttempt((a) => a + 1);
  }

  const progress = Math.round((stepsShown / STEPS.length) * 100);

  return (
    <main className="min-h-screen flex items-center justify-center bg-background text-foreground relative overflow-hidden px-4">
      <div
        className="fixed inset-0 pointer-events-none opacity-60"
        style={{
          backgroundImage:
            "linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px)",
          backgroundSize: "40px 40px",
        }}
      />
      <div
        className="fixed top-1/4 left-1/2 -translate-x-1/2 w-[34rem] h-[34rem] rounded-full blur-3xl pointer-events-none motion-safe:animate-[auth-glow-pulse_4s_ease-in-out_infinite]"
        style={{ background: "radial-gradient(circle, rgba(16,217,140,0.35), transparent 70%)" }}
      />

      <section className="relative w-full max-w-md" aria-live="polite">
        <div className="flex items-center gap-3 mb-8">
          <div className="w-10 h-10 rounded-xl bg-primary flex items-center justify-center shadow-[0_0_24px_rgba(16,217,140,0.5)]">
            <Wallet className="w-5 h-5 text-primary-foreground" />
          </div>
          <div>
            <p className="text-sm font-semibold tracking-tight">Wallit live demo</p>
            <p className="text-xs text-muted-foreground">Sample data, real analysis</p>
          </div>
        </div>

        <div className="rounded-2xl border border-border bg-card/80 backdrop-blur-xl p-5 sm:p-6 shadow-[0_30px_80px_-30px_rgba(0,0,0,0.8)]">
          <div className="flex items-center justify-between mb-4">
            <span className="text-[10px] font-mono uppercase tracking-[0.2em] text-muted-foreground">
              {status === "error" ? "boot failed" : "spinning up your sandbox"}
            </span>
            <span className="text-[11px] font-mono text-primary tabular-nums">{progress}%</span>
          </div>

          <div className="h-1 rounded-full bg-muted overflow-hidden mb-5">
            <div
              className={`h-full rounded-full transition-[width] duration-500 ease-out ${
                status === "error" ? "bg-destructive" : "bg-primary"
              }`}
              style={{ width: `${progress}%` }}
            />
          </div>

          <ol className="space-y-3">
            {STEPS.map((step, i) => {
              const visible = i < stepsShown;
              const done = i < stepsShown - 1 || finished;
              return (
                <li
                  key={step.label}
                  className={`flex items-start gap-3 transition-all duration-300 ${
                    visible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-1"
                  }`}
                >
                  <span
                    className={`mt-0.5 w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 ${
                      done ? "bg-primary/15 text-primary" : "bg-muted text-muted-foreground"
                    }`}
                  >
                    {done ? (
                      <Check className="w-3 h-3" strokeWidth={3} />
                    ) : status === "error" ? (
                      <span className="w-1.5 h-1.5 rounded-full bg-destructive" />
                    ) : (
                      <Loader2 className="w-3 h-3 motion-safe:animate-spin" />
                    )}
                  </span>
                  <div className="min-w-0">
                    <p className="text-sm leading-5">{step.label}</p>
                    <p className="text-xs font-mono text-muted-foreground truncate">{step.detail}</p>
                  </div>
                </li>
              );
            })}
          </ol>

          {status === "error" && (
            <div className="mt-6 pt-5 border-t border-border">
              <p className="text-sm text-destructive mb-4">{error}</p>
              <div className="flex flex-col sm:flex-row gap-2">
                <Button onClick={retry} className="sm:flex-1">
                  Try again
                </Button>
                <Link href="/login" className="sm:flex-1">
                  <Button variant="secondary" className="w-full">
                    Back to sign in
                  </Button>
                </Link>
              </div>
            </div>
          )}
        </div>

        <p className="mt-5 text-xs text-muted-foreground text-center leading-relaxed">
          Everything you see is computed by Wallit&apos;s real pipeline from a generated bank history.
          Connecting a real bank is turned off in the demo.
        </p>
      </section>
    </main>
  );
}
