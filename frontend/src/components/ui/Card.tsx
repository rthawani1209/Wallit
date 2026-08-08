import { HTMLAttributes } from "react";

export function Card({
  className = "",
  children,
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={`bg-surface border border-border rounded-card shadow-sm ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}
