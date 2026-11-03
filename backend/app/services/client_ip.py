import logging

from fastapi import Request

from app.config import settings

logger = logging.getLogger(__name__)
_logged_chain = False


def client_ip(request: Request) -> str:
    """The visitor's IP as reported by our own proxies, never by the client.
    Taking the leftmost X-Forwarded-For entry would let anyone dodge a limit
    by sending a made-up header on every request."""
    global _logged_chain
    raw = request.headers.get("x-forwarded-for", "")
    if not _logged_chain and raw:
        # Logged once per process so the real proxy chain (and so the right
        # TRUSTED_PROXY_HOPS) can be read off the production logs.
        logger.info("X-Forwarded-For chain has %d entries; using hops=%d", raw.count(",") + 1, settings.proxy_hops)
        _logged_chain = True

    hops = settings.proxy_hops
    entries = [e.strip() for e in raw.split(",") if e.strip()]
    if hops > 0 and entries:
        # A shorter chain than expected means a proxy didn't append; the nearest
        # entry we have is still better than the proxy's own socket address.
        return entries[-hops] if len(entries) >= hops else entries[0]
    return request.client.host if request.client else "unknown"
