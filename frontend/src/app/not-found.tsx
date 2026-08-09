import Link from "next/link";
import { Compass, Wallet } from "lucide-react";
import { Button } from "@/components/ui/Button";

export default function NotFound() {
  return (
    <main className="min-h-screen flex items-center justify-center bg-background text-foreground relative overflow-hidden">
      <div
        className="fixed inset-0 pointer-events-none opacity-[0.4]"
        style={{
          backgroundImage:
            "linear-gradient(rgba(255,255,255,0.025) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.025) 1px, transparent 1px)",
          backgroundSize: "48px 48px",
        }}
      />
      <div
        className="fixed top-1/3 left-1/2 -translate-x-1/2 w-[36rem] h-[36rem] rounded-full opacity-[0.08] blur-3xl pointer-events-none"
        style={{ background: "radial-gradient(circle, #10d98c, transparent 70%)" }}
      />

      <div className="relative flex flex-col items-center text-center px-6">
        <div className="w-12 h-12 rounded-xl bg-primary flex items-center justify-center shadow-[0_0_20px_rgba(16,217,140,0.45)] mb-6">
          <Wallet className="w-6 h-6 text-primary-foreground" />
        </div>
        <p className="text-sm font-mono text-muted-foreground mb-2">404</p>
        <h1 className="text-2xl font-semibold tracking-tight mb-2">Page not found</h1>
        <p className="text-sm text-muted-foreground mb-8 max-w-sm">
          That page doesn't exist, or it moved. Let's get you back to your finances.
        </p>
        <Link href="/dashboard">
          <Button className="gap-2">
            <Compass className="w-4 h-4" />
            Back to Dashboard
          </Button>
        </Link>
      </div>
    </main>
  );
}
