import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

// A dedicated demo hostname (e.g. wallit-demo.vercel.app, added as a second
// domain on the same Vercel project) skips the login screen and drops visitors
// straight into the sandbox. Every other host is untouched.
const DEMO_HOST_PREFIX = "wallit-demo";

export function proxy(request: NextRequest) {
  const host = request.headers.get("host") ?? "";
  if (host.startsWith(DEMO_HOST_PREFIX)) {
    return NextResponse.redirect(new URL("/demo", request.url));
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/", "/login", "/signup"],
};
