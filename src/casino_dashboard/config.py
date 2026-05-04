"""Casino Dashboard configuration — reads env vars, exposes typed constants."""
import logging
import os

logger = logging.getLogger(__name__)


def _require(name: str) -> str:
    val = os.environ.get(name)
    if not val:
        raise EnvironmentError(f"Required env var {name!r} is not set")
    return val


def get_reddit_credentials() -> tuple[str, str, str] | None:
    """Return (client_id, client_secret, user_agent) or None if any are missing."""
    client_id = os.environ.get("REDDIT_CLIENT_ID")
    client_secret = os.environ.get("REDDIT_CLIENT_SECRET")
    user_agent = os.environ.get("REDDIT_USER_AGENT")

    if not client_id or not client_secret or not user_agent:
        missing = [
            name
            for name, val in [
                ("REDDIT_CLIENT_ID", client_id),
                ("REDDIT_CLIENT_SECRET", client_secret),
                ("REDDIT_USER_AGENT", user_agent),
            ]
            if not val
        ]
        logger.warning(
            "Reddit credentials missing (%s) — Reddit collection will be skipped",
            ", ".join(missing),
        )
        return None

    return client_id, client_secret, user_agent
