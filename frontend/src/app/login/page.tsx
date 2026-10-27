"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Input, Label } from "@/components/ui/Input";
import { AuthLayout } from "@/components/auth/AuthLayout";
import { AuthDivider, GoogleButton } from "@/components/auth/GoogleButton";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await api.auth.login(email, password);
      router.push("/dashboard");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthLayout>
      <h1 className="text-2xl font-bold mb-1 text-foreground tracking-tight">
        Welcome back
      </h1>
      <p className="text-sm text-muted-foreground mb-6">Sign in to your Wallit account</p>

      <GoogleButton label="Continue with Google" />
      <AuthDivider />

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <Label htmlFor="email">Email</Label>
          <Input
            id="email"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </div>
        <div>
          <Label htmlFor="password">Password</Label>
          <Input
            id="password"
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>
        {error && <p className="text-destructive text-sm">{error}</p>}
        <Button
          type="submit"
          loading={loading}
          loadingText="Signing in…"
          className="w-full"
        >
          Sign in
        </Button>
      </form>

      <Link
        href="/demo"
        className="mt-4 group flex items-center justify-between rounded-lg border border-primary/25 bg-primary/[0.06] px-4 py-3 transition-colors hover:bg-primary/[0.1]"
      >
        <span>
          <span className="block text-sm font-medium text-foreground">Explore the live demo</span>
          <span className="block text-xs text-muted-foreground">No account needed. Sample data, real analysis.</span>
        </span>
        <span className="text-primary transition-transform group-hover:translate-x-0.5" aria-hidden="true">
          →
        </span>
      </Link>

      <p className="mt-6 text-sm text-center text-muted-foreground">
        Don&apos;t have an account?{" "}
        <Link href="/signup" className="text-primary hover:underline">
          Sign up
        </Link>
      </p>
    </AuthLayout>
  );
}
