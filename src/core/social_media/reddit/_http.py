"""Shared HTTP configuration for the Reddit-family clients.

Reddit frequently returns 403 "Blocked" for unauthenticated requests coming
from datacenter/cloud IP ranges (AWS, GCP, Azure, GitHub Actions). Two knobs
help work around that without code changes:

- ``REDDIT_USER_AGENT`` — override the User-Agent. Reddit asks for a unique,
  descriptive agent; a generic or empty one is more likely to be throttled.
- ``REDDIT_PROXY`` — route outbound Reddit traffic through a proxy (e.g. a
  residential/allowed IP) so cloud runs are not blocked. Applied to both http
  and https. Example: ``http://user:pass@host:port``.

Both are read from the environment at call time, so they can be set per-run
(locally or as CI secrets/vars) with no redeploy.
"""
import os

_DEFAULT_USER_AGENT = (
    "casino-dashboard/0.1 (personal stock dashboard; "
    "+https://github.com/gopichandkommineni/ticker-video-digest)"
)


def reddit_user_agent() -> str:
    """The User-Agent to send on Reddit requests (REDDIT_USER_AGENT or default)."""
    return os.environ.get("REDDIT_USER_AGENT", "").strip() or _DEFAULT_USER_AGENT


def reddit_proxy_url() -> str | None:
    """The configured proxy URL (REDDIT_PROXY), or None when unset."""
    return os.environ.get("REDDIT_PROXY", "").strip() or None


def reddit_proxies() -> dict[str, str] | None:
    """A ``requests``-style proxies dict, or None when no proxy is configured."""
    proxy = reddit_proxy_url()
    if not proxy:
        return None
    return {"http": proxy, "https": proxy}
