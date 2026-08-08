import { Button } from "./Button";

interface NavProps {
  userEmail: string;
  onLogout: () => void;
}

export function Nav({ userEmail, onLogout }: NavProps) {
  return (
    <nav className="bg-surface border-b border-border px-6 py-4 flex items-center justify-between">
      <h1 className="text-xl font-bold text-foreground tracking-tight">Wallit</h1>
      <div className="flex items-center gap-4">
        <span className="text-sm text-muted">{userEmail}</span>
        <Button variant="ghost" onClick={onLogout}>
          Log out
        </Button>
      </div>
    </nav>
  );
}
