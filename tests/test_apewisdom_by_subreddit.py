"""Tests for the ApeWisdom per-subreddit breakdown stage (network mocked)."""
import sqlite3
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest

from casino_dashboard.data.models import ApeWisdomMention
from casino_dashboard.db.repository import get_social_history, get_latest_social_mentions
from casino_dashboard.db.schema import init_db
from casino_dashboard.jobs.daily_refresh import _refresh_apewisdom_by_subreddit


@pytest.fixture
def db(tmp_path: Path) -> Path:
    path = tmp_path / "t.db"
    init_db(path)
    return path


def test_per_subreddit_rows_saved_and_isolated(db: Path):
    by_sub = {
        "wallstreetbets": [ApeWisdomMention("RKLB", 300, 200, 5000)],
        "stocks": [ApeWisdomMention("RKLB", 40, 30, 800),
                   ApeWisdomMention("ZZZ", 1, 1, 1)],  # ZZZ not in universe
    }

    with patch("casino_dashboard.jobs.refresh_sources.fetch_apewisdom_universe",
               side_effect=lambda sub: by_sub.get(sub, [])), \
         patch.dict("os.environ", {"APEWISDOM_SUBREDDITS": "wallstreetbets,stocks"}):
        saved, n = _refresh_apewisdom_by_subreddit(["RKLB"], date(2026, 8, 15), db)

    assert n == 2
    assert saved == 2  # RKLB in wsb + RKLB in stocks; ZZZ filtered out

    # Stored under source='apewisdom' with the subreddit tag.
    with sqlite3.connect(db) as conn:
        rows = conn.execute(
            "SELECT subreddit, mention_count FROM social_mentions "
            "WHERE ticker='RKLB' AND source='apewisdom' ORDER BY subreddit"
        ).fetchall()
    assert rows == [("stocks", 40), ("wallstreetbets", 300)]

    # The per-subreddit rows must NOT leak into the aggregate (subreddit='') views.
    assert get_social_history("RKLB", "apewisdom", 30, db).empty
    assert get_latest_social_mentions(db).empty


def test_subreddit_failure_is_isolated(db: Path):
    def flaky(sub):
        if sub == "bad":
            raise RuntimeError("boom")
        return [ApeWisdomMention("RKLB", 10, 5, 100)]

    with patch("casino_dashboard.jobs.refresh_sources.fetch_apewisdom_universe", side_effect=flaky), \
         patch.dict("os.environ", {"APEWISDOM_SUBREDDITS": "bad,stocks"}):
        saved, n = _refresh_apewisdom_by_subreddit(["RKLB"], date(2026, 8, 15), db)

    assert n == 2 and saved == 1  # bad skipped, stocks saved
