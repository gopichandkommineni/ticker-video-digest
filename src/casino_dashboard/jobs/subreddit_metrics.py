"""Direct subreddit-metrics probe — Arctic Shift backend, no credentials.

Takes one or more subreddit NAMES (not tickers) and prints the community metrics
Arctic Shift exposes for each: subscribers, recent-post volume, description, and
NSFW/quarantine flags. Unlike subreddit_discovery_run, there is no candidate
generation or relevance scoring — you name the sub, you get its raw metrics.

Arctic Shift is a public archive API (arctic-shift.photon-reddit.com), NOT
reddit.com, so it is reachable from GitHub Actions runners where reddit.com is
IP-blocked. This is what lets the probe run on a runner at all.

Writes NOTHING to the database and commits NOTHING — safe to run on demand.

Usage:
    python -m casino_dashboard.jobs.subreddit_metrics RKLB RocketLab IonQStock
    python -m casino_dashboard.jobs.subreddit_metrics r/RKLB /r/RocketLab
    SUBREDDIT_METRICS_NAMES="RKLB,RocketLab,IonQStock" \
        python -m casino_dashboard.jobs.subreddit_metrics

In GitHub Actions the report is also appended to $GITHUB_STEP_SUMMARY.
"""
import logging
import os
import re
import sys
import time

from core.social_media.reddit.subreddit_discovery import (
    SubredditInfo,
    count_recent_posts,
    fetch_about,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

_REQUEST_DELAY = 0.5  # polite pause between Arctic Shift calls
_DEFAULT_NAMES = ["RKLB", "RocketLab", "IonQStock"]


def _clean_name(raw: str) -> str:
    """Strip a leading r/ or /r/ and surrounding whitespace: '/r/RKLB' -> 'RKLB'."""
    return re.sub(r"^/?r/", "", raw.strip(), flags=re.IGNORECASE).strip()


def _resolve_names(argv: list[str]) -> list[str]:
    if argv:
        raw = argv
    else:
        env = os.environ.get("SUBREDDIT_METRICS_NAMES", "").strip()
        raw = env.split(",") if env else _DEFAULT_NAMES
    names: list[str] = []
    for item in raw:
        name = _clean_name(item)
        if name and name not in names:
            names.append(name)
    return names


def _metrics_row(name: str, info: SubredditInfo | None) -> str:
    if info is None:
        return f"| r/{name} | — | — | — | — | 🚩 not found on Arctic Shift |"
    flags = []
    if info.over18:
        flags.append("NSFW")
    if info.quarantined:
        flags.append("quarantined")
    flag_text = ", ".join(flags) if flags else "—"
    desc = (info.public_description or info.title or "").replace("\n", " ").strip()
    if len(desc) > 80:
        desc = desc[:77] + "…"
    return (
        f"| [r/{info.name}](https://reddit.com/r/{info.name}) "
        f"| {info.subscribers:,} | {info.posts_7d} | {flag_text} | {desc or '—'} |"
    )


def run(names: list[str], sleep: bool = True) -> list[str]:
    """Fetch metrics for each subreddit and return Markdown report lines."""
    lines: list[str] = [
        "## Subreddit metrics (Arctic Shift)",
        "",
        "| Subreddit | Subscribers | Posts/7d | Flags | Description |",
        "|-----------|-------------|----------|-------|-------------|",
    ]
    for raw in names:
        name = _clean_name(raw)
        if not name:
            continue
        logger.info("Fetching Arctic Shift metrics for r/%s …", name)
        info = fetch_about(name)
        if sleep:
            time.sleep(_REQUEST_DELAY)
        if info is not None:
            info.posts_7d = count_recent_posts(info.name)
            if sleep:
                time.sleep(_REQUEST_DELAY)
        lines.append(_metrics_row(name, info))
    lines.append("")
    lines.append(
        "_Posts/7d is a lower bound (Arctic Shift returns at most ~100 recent "
        "posts per query) and lags real time by 1–2 days. Live 'users online' "
        "and moderator-only traffic stats are not available._"
    )
    lines.append("")
    return lines


def main() -> None:
    names = _resolve_names(sys.argv[1:])
    if not names:
        logger.error("No subreddit names supplied.")
        sys.exit(1)
    lines = run(names)
    report = "\n".join(lines) + "\n"
    print("\n" + report)

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a") as f:
            f.write(report)


if __name__ == "__main__":
    main()
