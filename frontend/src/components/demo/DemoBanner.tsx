"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { FlaskConical } from "lucide-react";
import { api } from "@/lib/api";

// Pages that sit outside the signed-in app never show the banner.
const APP_ROUTES = ["/dashboard", "/calendar", "/subscriptions", "/assistant"];

export function DemoBanner() {
  const pathname = usePathname();
  const onAppRoute = APP_ROUTES.some((route) => pathname.startsWith(route));
  const [isDemo, setIsDemo] = useState(false);

  useEffect(() => {
    if (!onAppRoute) return;
    let cancelled = false;
    api.auth
      .me()
      .then((user) => !cancelled && setIsDemo(user.is_demo))
      .catch(() => !cancelled && setIsDemo(false));
    return () => {
      cancelled = true;
    };
  }, [onAppRoute, pathname]);

  if (!onAppRoute || !isDemo) return null;

  return (
    <div className="md:hidden sticky top-0 z-30 flex items-center gap-2 px-4 py-2 text-xs border-b border-primary/20 bg-[rgba(7,16,31,0.92)] backdrop-blur">
      <FlaskConical className="w-3.5 h-3.5 text-primary flex-shrink-0" />
      <span className="text-muted-foreground truncate">
        <span className="text-foreground font-medium">Demo</span> · sample data, real analysis
      </span>
      <Link href="/signup" className="ml-auto text-primary font-semibold flex-shrink-0">
        Sign up
      </Link>
    </div>
  );
}
