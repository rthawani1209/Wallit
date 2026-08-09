import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // In production, BACKEND_URL proxies /api/* through this same domain instead
  // of the browser calling the Railway domain directly — makes the login
  // cookie same-site instead of cross-site, which mobile Safari otherwise
  // blocks. Unset locally, so local dev is unaffected (direct calls to
  // NEXT_PUBLIC_API_URL as before).
  async rewrites() {
    const backend = process.env.BACKEND_URL;
    if (!backend) return [];
    return [{ source: "/api/:path*", destination: `${backend}/api/:path*` }];
  },
};

export default nextConfig;
