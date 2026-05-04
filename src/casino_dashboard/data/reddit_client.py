"""Reddit (PRAW) client for per-subreddit social mention tracking."""
import logging
import re
from dataclasses import dataclass

from casino_dashboard.config import get_reddit_credentials

logger = logging.getLogger(__name__)

SUBREDDITS = ["wallstreetbets", "stocks", "pennystocks", "Daytrading", "options"]

# Tickers that are also common English words/abbreviations — require $ prefix to disambiguate
AMBIGUOUS_TICKERS = {"AG", "MP", "NB", "FN", "PL", "CDE", "POET"}


@dataclass
class RedditMention:
    ticker: str
    subreddit: str
    mention_count: int
    upvote_sum: int


def build_ticker_pattern(ticker: str) -> re.Pattern:
    """Return a compiled regex for matching a ticker in Reddit text.

    Ambiguous tickers (common words) require a $ prefix so 'AG' won't match
    'AGAIN' or 'AGENCY'. Unambiguous tickers match $TICKER or bare TICKER.
    """
    ticker_upper = ticker.upper()
    if ticker_upper in AMBIGUOUS_TICKERS:
        # Only match with $ prefix to avoid false positives
        pattern = rf"\${re.escape(ticker_upper)}\b"
    else:
        # Match $TICKER or bare TICKER (word boundary on right; left boundary via \b or $)
        pattern = rf"(\$|\b){re.escape(ticker_upper)}\b"
    return re.compile(pattern, re.IGNORECASE)


def get_reddit_client():
    """Return a read-only praw.Reddit instance, or None if credentials are missing."""
    try:
        import praw
    except ImportError:
        logger.warning("praw not installed — Reddit collection unavailable")
        return None

    creds = get_reddit_credentials()
    if creds is None:
        return None

    client_id, client_secret, user_agent = creds
    return praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent,
        read_only=True,
    )


def count_mentions_in_subreddit(
    reddit,
    subreddit_name: str,
    ticker: str,
    hours: int = 24,
) -> "RedditMention":
    """Search one subreddit for posts mentioning a ticker and count matches.

    Counts: 1 per matching post + 1 per top-level comment whose body matches.
    Sums upvotes across all matching items.
    Returns zero counts on any error rather than propagating exceptions.
    """
    pattern = build_ticker_pattern(ticker)
    mention_count = 0
    upvote_sum = 0

    try:
        subreddit = reddit.subreddit(subreddit_name)
        posts = subreddit.search(
            query=f"${ticker}",
            sort="new",
            time_filter="day",
            limit=100,
        )

        for post in posts:
            post_text = (post.title or "") + " " + (post.selftext or "")
            if pattern.search(post_text):
                mention_count += 1
                upvote_sum += max(0, post.score or 0)

                # Count top-level comments
                try:
                    post.comments.replace_more(limit=0)
                    for comment in post.comments:
                        if pattern.search(comment.body or ""):
                            mention_count += 1
                            upvote_sum += max(0, comment.score or 0)
                except Exception as exc:
                    logger.debug(
                        "Error reading comments for post %s in r/%s: %s",
                        getattr(post, "id", "?"),
                        subreddit_name,
                        exc,
                    )

    except Exception as exc:
        logger.warning(
            "Reddit search failed for %s in r/%s: %s — returning zeros",
            ticker,
            subreddit_name,
            exc,
        )

    return RedditMention(
        ticker=ticker,
        subreddit=subreddit_name,
        mention_count=mention_count,
        upvote_sum=upvote_sum,
    )


def fetch_reddit_mentions_for_universe(
    reddit,
    tickers: list[str],
) -> list["RedditMention"]:
    """Fetch per-subreddit mention counts for every ticker in the universe.

    Returns a flat list of RedditMention (one per ticker × subreddit pair).
    If reddit is None, returns an empty list immediately.
    """
    if reddit is None:
        return []

    results: list[RedditMention] = []
    total = len(tickers)

    for i, ticker in enumerate(tickers):
        if i > 0 and i % 10 == 0:
            logger.info("Reddit progress: %d/%d tickers", i, total)

        for sub in SUBREDDITS:
            mention = count_mentions_in_subreddit(reddit, sub, ticker)
            results.append(mention)

    logger.info("Reddit progress: %d/%d tickers", total, total)
    return results
