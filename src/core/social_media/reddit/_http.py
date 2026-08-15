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


def reddit_impersonate() -> str | None:
    """Browser profile to impersonate at the TLS layer, or None to disable.

    Reddit 403-blocks requests that don't look like a real browser — not just by
    User-Agent but by the TLS/HTTP handshake fingerprint. curl_cffi can mimic a
    real Chrome fingerprint so Reddit serves us. Controlled by REDDIT_IMPERSONATE
    (default 'chrome'); set it to 'none'/'off'/'' to disable and use plain
    requests.
    """
    value = os.environ.get("REDDIT_IMPERSONATE", "chrome").strip()
    if value.lower() in ("", "none", "off", "0", "false"):
        return None
    return value


def reddit_get(url: str, params: dict | None = None, timeout: int = 10):
    """GET a Reddit URL looking like a real browser.

    Uses curl_cffi with a Chrome fingerprint when available (the reliable way
    past Reddit's bot block); falls back to plain ``requests`` if curl_cffi is
    missing or impersonation is disabled. Honors REDDIT_USER_AGENT and
    REDDIT_PROXY. Returns a requests-compatible response (``.status_code``,
    ``.json()``, ``.raise_for_status()``).
    """
    proxies = reddit_proxies()
    ua = os.environ.get("REDDIT_USER_AGENT", "").strip()
    impersonate = reddit_impersonate()

    if impersonate is not None:
        try:
            from curl_cffi import requests as cffi_requests  # noqa: PLC0415

            # When impersonating, curl_cffi supplies a matching browser
            # User-Agent; only override it if the caller set one explicitly.
            headers = {"User-Agent": ua} if ua else None
            return cffi_requests.get(
                url,
                params=params,
                timeout=timeout,
                impersonate=impersonate,
                headers=headers,
                proxies=proxies,
            )
        except ImportError:
            pass  # curl_cffi unavailable — fall back to plain requests below

    import requests  # noqa: PLC0415

    return requests.get(
        url,
        params=params,
        timeout=timeout,
        headers={"User-Agent": ua or reddit_user_agent()},
        proxies=proxies,
    )
