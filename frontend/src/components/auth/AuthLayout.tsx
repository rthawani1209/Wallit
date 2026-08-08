import { LineChart, PieChart, Target, TrendingUp, Wallet } from "lucide-react";

const FEATURES = [
  {
    icon: LineChart,
    title: "Cash flow tracking",
    description: "Income and expenses, visualized month over month.",
  },
  {
    icon: PieChart,
    title: "Automatic categorization",
    description: "Every transaction sorted into a category — no manual tagging.",
  },
  {
    icon: Target,
    title: "Budgets that keep up",
    description: "Limits suggested from your real spending, editable anytime.",
  },
];

const GRID_BACKGROUND = {
  backgroundImage:
    "linear-gradient(rgba(255,255,255,0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.04) 1px, transparent 1px)",
  backgroundSize: "44px 44px",
};

export function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <main className="min-h-screen flex bg-background">
      <div className="hidden lg:flex lg:w-1/2 relative overflow-hidden bg-sidebar border-r border-border">
        <div className="absolute inset-0" style={GRID_BACKGROUND} />
        <div
          className="absolute inset-0"
          style={{
            background:
              "radial-gradient(ellipse 80% 60% at 50% 0%, rgba(7,16,31,0) 0%, var(--sidebar) 75%)",
          }}
        />
        <div
          className="absolute -top-32 -left-32 w-[30rem] h-[30rem] rounded-full blur-3xl"
          style={{
            background: "radial-gradient(circle, #10d98c, transparent 70%)",
            animation: "auth-glow-pulse 7s ease-in-out infinite",
          }}
        />
        <div
          className="absolute bottom-0 -right-20 w-96 h-96 rounded-full blur-3xl"
          style={{
            background: "radial-gradient(circle, #6366f1, transparent 70%)",
            animation: "auth-glow-pulse 7s ease-in-out infinite 2s",
          }}
        />

        {/* Floating preview cards — pushed to the corners so they're ambient
            background texture, not competing with the wordmark for attention. */}
        <div
          className="absolute top-10 right-6 w-48 rounded-2xl border border-white/10 bg-white/[0.04] backdrop-blur-xl p-4 shadow-2xl hidden xl:block opacity-80"
          style={{ animation: "auth-float-b 8s ease-in-out infinite" }}
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
              Cash Flow
            </span>
            <TrendingUp className="w-3.5 h-3.5 text-primary" />
          </div>
          <div className="h-10 flex items-end gap-1">
            {[40, 55, 45, 70, 60, 85, 78].map((h, i) => (
              <div key={i} className="flex-1 rounded-sm bg-primary/60" style={{ height: `${h}%` }} />
            ))}
          </div>
        </div>

        <div
          className="absolute bottom-10 left-6 w-52 rounded-2xl p-5 shadow-2xl overflow-hidden hidden xl:block opacity-90"
          style={{
            background: "linear-gradient(135deg, #10d98c 0%, #059669 100%)",
            animation: "auth-float-a 9s ease-in-out infinite",
          }}
        >
          <div className="absolute -right-4 -top-4 w-20 h-20 rounded-full opacity-10 bg-white" />
          <span
            className="text-[10px] font-semibold uppercase tracking-widest block mb-2"
            style={{ color: "rgba(7,16,31,0.65)" }}
          >
            Total Balance
          </span>
          <div className="text-2xl font-bold tracking-tight font-mono" style={{ color: "#07101f" }}>
            $••,•••.••
          </div>
        </div>

        <div className="relative flex flex-col items-center justify-center flex-1 text-center px-10 xl:px-16 py-12">
          {/* HUD-style rings behind the wordmark */}
          <div
            className="absolute w-64 h-64 rounded-full border border-primary/25 pointer-events-none"
            style={{ animation: "auth-ring-pulse 5s ease-in-out infinite" }}
          />
          <div
            className="absolute w-80 h-80 rounded-full border border-dashed border-primary/10 pointer-events-none"
            style={{ animation: "auth-ring-rotate 50s linear infinite" }}
          />
          <div className="absolute w-[26rem] h-[26rem] rounded-full border border-white/[0.04] pointer-events-none" />

          <span className="relative font-mono text-[11px] tracking-[0.35em] text-primary/70 uppercase mb-4">
            Financial OS
          </span>

          <div className="relative flex items-center gap-4 mb-8">
            <div className="w-14 h-14 rounded-2xl bg-primary flex items-center justify-center shadow-[0_0_40px_rgba(16,217,140,0.5)]">
              <Wallet className="w-7 h-7 text-primary-foreground" />
            </div>
            <span
              className="font-bold text-6xl xl:text-7xl tracking-tight bg-clip-text text-transparent"
              style={{
                backgroundImage: "linear-gradient(135deg, #ffffff 25%, #7de8c4 100%)",
                filter: "drop-shadow(0 0 30px rgba(16,217,140,0.3))",
              }}
            >
              Wallit
            </span>
          </div>

          <h1 className="relative text-3xl xl:text-4xl font-bold tracking-tight text-foreground mb-3 max-w-md leading-[1.15]">
            See your whole financial picture in one place.
          </h1>
          <p className="relative text-sm text-muted-foreground max-w-sm mb-10">
            Wallit connects to your accounts and automatically organizes your spending —
            no spreadsheets required.
          </p>

          <div className="relative space-y-3 w-full max-w-sm text-left">
            {FEATURES.map(({ icon: Icon, title, description }) => (
              <div
                key={title}
                className="flex items-start gap-3 rounded-xl border border-white/[0.06] bg-white/[0.03] backdrop-blur-sm p-3.5"
              >
                <div className="w-9 h-9 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
                  <Icon className="w-4 h-4 text-primary" />
                </div>
                <div>
                  <p className="text-sm font-medium text-foreground">{title}</p>
                  <p className="text-xs text-muted-foreground mt-0.5">{description}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="flex-1 flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-sm">
          <div className="lg:hidden flex items-center gap-2.5 mb-8 justify-center">
            <div className="w-8 h-8 rounded-xl bg-primary flex items-center justify-center">
              <Wallet className="w-4 h-4 text-primary-foreground" />
            </div>
            <span className="font-semibold text-[15px] tracking-tight text-foreground">
              Wallit
            </span>
          </div>
          {children}
        </div>
      </div>
    </main>
  );
}
