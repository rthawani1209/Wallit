import { InputHTMLAttributes, LabelHTMLAttributes } from "react";

export function Label({
  className = "",
  children,
  ...props
}: LabelHTMLAttributes<HTMLLabelElement>) {
  return (
    <label
      className={`block text-sm font-medium text-foreground mb-1.5 ${className}`}
      {...props}
    >
      {children}
    </label>
  );
}

export function Input({
  className = "",
  ...props
}: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={`h-9 w-full rounded-md border border-border bg-input px-3 py-1 text-sm text-foreground placeholder:text-muted-foreground outline-none transition-colors focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/50 disabled:opacity-50 ${className}`}
      {...props}
    />
  );
}
