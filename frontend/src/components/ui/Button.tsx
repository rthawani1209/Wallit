"use client";

import { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "destructive" | "secondary" | "outline" | "ghost";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  loading?: boolean;
  loadingText?: string;
}

const variantClasses: Record<Variant, string> = {
  primary: "bg-primary text-primary-foreground hover:bg-primary/90",
  destructive: "bg-destructive text-destructive-foreground hover:bg-destructive/90",
  secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/80",
  outline: "border border-border bg-transparent text-foreground hover:bg-secondary",
  ghost: "bg-transparent text-primary hover:underline px-0",
};

export function Button({
  variant = "primary",
  loading = false,
  loadingText,
  disabled,
  className = "",
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      disabled={disabled || loading}
      className={`inline-flex items-center justify-center rounded-md px-4 py-2 text-sm font-medium transition-colors disabled:pointer-events-none disabled:opacity-50 ${variantClasses[variant]} ${className}`}
      {...props}
    >
      {loading ? loadingText ?? "Loading…" : children}
    </button>
  );
}
