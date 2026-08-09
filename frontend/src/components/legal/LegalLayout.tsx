import Link from "next/link";
import { Wallet } from "lucide-react";

export function LegalLayout({
  title,
  updated,
  children,
}: {
  title: string;
  updated: string;
  children: React.ReactNode;
}) {
  return (
    <main className="min-h-screen bg-background text-foreground">
      <header className="border-b border-border px-4 md:px-8 py-4">
        <Link href="/login" className="inline-flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-xl bg-primary flex items-center justify-center">
            <Wallet className="w-4 h-4 text-primary-foreground" />
          </div>
          <span className="font-semibold text-[15px] tracking-tight">Wallit</span>
        </Link>
      </header>

      <div className="max-w-2xl mx-auto px-4 md:px-8 py-12">
        <h1 className="text-3xl font-bold tracking-tight mb-1.5">{title}</h1>
        <p className="text-xs text-muted-foreground mb-10">Last updated {updated}</p>
        <div className="space-y-6 text-sm leading-relaxed text-foreground/90 [&_h2]:text-base [&_h2]:font-semibold [&_h2]:text-foreground [&_h2]:tracking-tight [&_h2]:mt-2 [&_p]:mb-0 [&_ul]:list-disc [&_ul]:pl-5 [&_ul]:space-y-1.5 [&_a]:text-primary [&_a]:hover:underline">
          {children}
        </div>

        <div className="mt-14 pt-6 border-t border-border flex gap-4 text-xs text-muted-foreground">
          <Link href="/privacy" className="hover:text-foreground transition-colors">Privacy Policy</Link>
          <Link href="/terms" className="hover:text-foreground transition-colors">Terms of Service</Link>
          <Link href="/login" className="hover:text-foreground transition-colors">Back to Wallit</Link>
        </div>
      </div>
    </main>
  );
}
