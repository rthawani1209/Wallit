import { LineChart, PieChart, Target, Wallet } from "lucide-react";

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

export function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <main className="min-h-screen flex bg-background">
      <div className="hidden lg:flex lg:w-[45%] relative overflow-hidden bg-sidebar border-r border-border">
        <div
          className="absolute -top-24 -left-24 w-96 h-96 rounded-full opacity-[0.15] blur-3xl"
          style={{ background: "radial-gradient(circle, #10d98c, transparent 70%)" }}
        />
        <div
          className="absolute bottom-0 right-0 w-80 h-80 rounded-full opacity-10 blur-3xl"
          style={{ background: "radial-gradient(circle, #6366f1, transparent 70%)" }}
        />

        <div className="relative flex flex-col justify-between p-12 w-full">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-primary flex items-center justify-center">
              <Wallet className="w-4 h-4 text-primary-foreground" />
            </div>
            <span className="font-semibold text-[15px] tracking-tight text-sidebar-foreground">
              Wallit
            </span>
          </div>

          <div>
            <h1 className="text-3xl font-bold tracking-tight text-foreground mb-3 max-w-sm">
              See your whole financial picture in one place.
            </h1>
            <p className="text-sm text-muted-foreground max-w-sm mb-10">
              Wallit connects to your accounts and automatically organizes your spending —
              no spreadsheets required.
            </p>

            <div className="space-y-5">
              {FEATURES.map(({ icon: Icon, title, description }) => (
                <div key={title} className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-lg bg-secondary flex items-center justify-center shrink-0 mt-0.5">
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

          <div />
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
