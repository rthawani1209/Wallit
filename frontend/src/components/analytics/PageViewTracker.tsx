"use client";

import { useEffect } from "react";
import { usePathname } from "next/navigation";
import { api } from "@/lib/api";

const VISITOR_KEY = "wallit-visitor";

// A random id per browser so visits before sign-up can be counted. It isn't
// tied to anything else about the visitor.
function visitorId(): string | null {
  try {
    let id = localStorage.getItem(VISITOR_KEY);
    if (!id) {
      id = crypto.randomUUID();
      localStorage.setItem(VISITOR_KEY, id);
    }
    return id;
  } catch {
    return null; // storage blocked (private window, strict settings)
  }
}

function optedOut(): boolean {
  const nav = navigator as Navigator & { globalPrivacyControl?: boolean };
  return nav.doNotTrack === "1" || nav.globalPrivacyControl === true;
}

/** Reports each page view to our own backend. The backend ignores pages it
 * doesn't track, so this sends the path as-is. */
export function PageViewTracker() {
  const pathname = usePathname();

  useEffect(() => {
    if (!pathname || optedOut()) return;
    const id = visitorId();
    if (id) api.events.pageView(pathname, id).catch(() => {});
  }, [pathname]);

  return null;
}
