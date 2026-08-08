import { HTMLAttributes } from "react";

export function Card({
  className = "",
  children,
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={`bg-card text-card-foreground rounded-2xl border border-border ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}
