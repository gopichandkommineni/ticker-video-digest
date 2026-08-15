"""Unit tests for subreddit discovery — no real network calls."""
import time
from unittest.mock import MagicMock, patch

from core.social_media.reddit import subreddit_discovery as sd
from core.social_media.reddit.subreddit_discovery import (
    SubredditInfo,
    _valid_subreddit_name,
    discover,
    generate_candidates,
    score_subreddit,
)


# ---------------------------------------------------------------------------
# Candidate generation
# ---------------------------------------------------------------------------

def test_generate_candidates_ticker_patterns():
    cands = generate_candidates("RKLB")
    assert "RKLB" in cands
    assert "RKLBstock" in cands
    assert "RKLB_investors" in cands
    # all syntactically valid
    assert all(_valid_subreddit_name(c) for c in cands)


def test_generate_candidates_company_name_variants():
    cands = generate_candidates("RKLB", company_name="Rocket Lab USA, Inc.")
    assert "RocketLab" in cands       # suffixes stripped, joined
    assert "Rocket_Lab" in cands      # underscored
    assert "rocketlab" in cands       # lowercased variant


def test_generate_candidates_dedupes_and_caps():
    cands = generate_candidates("AAA", extra_seeds=["AAA", "AAA", "AAAextra"])
    assert cands.count("AAA") == 1
    assert len(cands) <= sd._MAX_CANDIDATES


def test_valid_subreddit_name_rules():
    assert _valid_subreddit_name("RKLB")
    assert _valid_subreddit_name("Rocket_Lab")
    assert not _valid_subreddit_name("ab")        # too short
    assert not _valid_subreddit_name("has space")
    assert not _valid_subreddit_name("bad-dash")


# ---------------------------------------------------------------------------
# Scoring / selection
# ---------------------------------------------------------------------------

def _info(name, subs, posts=5, online=10, desc="", title="", quarantined=False):
    return SubredditInfo(
        name=name, subscribers=subs, active_online=online,
        title=title, public_description=desc, posts_7d=posts, quarantined=quarantined,
    )


def test_real_community_selected():
    info = _info("RocketLab", 40000, posts=30, desc="Rocket Lab RKLB discussion")
    scored = score_subreddit(info, "RKLB", "Rocket Lab")
    assert scored.selected
    assert scored.relevance > 0
    assert scored.reasons == ["selected"]


def test_tiny_dead_sub_is_noise():
    info = _info("RKLBfanclub", 8, posts=0, desc="")
    scored = score_subreddit(info, "RKLB", "Rocket Lab")
    assert not scored.selected
    assert any("no posts" in r or "subscribers" in r for r in scored.reasons)


def test_irrelevant_name_not_selected_even_if_big():
    # Big sub, but nothing references the stock -> relevance 0 -> not selected.
    info = _info("worldnews", 5_000_000, posts=100, desc="news from around the world")
    scored = score_subreddit(info, "RKLB", "Rocket Lab")
    assert scored.relevance == 0
    assert not scored.selected


def test_quarantined_not_selected():
    info = _info("RKLBraw", 5000, posts=10, desc="RKLB", quarantined=True)
    scored = score_subreddit(info, "RKLB", "Rocket Lab")
    assert not scored.selected


# ---------------------------------------------------------------------------
# discover() — metrics sourced from Arctic Shift (mocked)
# ---------------------------------------------------------------------------

def test_discover_ranks_and_flags():
    subs = {
        "RKLB": {"display_name": "RKLB", "subscribers": 15000,
                 "public_description": "RKLB Rocket Lab stock"},
        "RocketLab": {"display_name": "RocketLab", "subscribers": 42000,
                      "public_description": "Rocket Lab discussion"},
    }

    def fake_subs(query=None, subreddit=None, limit=20):
        if subreddit:
            d = subs.get(subreddit)
            return [d] if d else []
        return [subs["RocketLab"]]

    with patch("core.social_media.reddit.arctic_shift_client.search_subreddits", side_effect=fake_subs), \
         patch("core.social_media.reddit.arctic_shift_client.count_posts_in_window",
               side_effect=lambda name, days=7: {"RKLB": 12, "RocketLab": 40}.get(name, 0)):
        result = discover("RKLB", company_name="Rocket Lab", sleep=False)

    names = [s.info.name for s in result.subreddits]
    assert "RocketLab" in names and "RKLB" in names
    assert result.found is True
    assert all(s.selected for s in result.subreddits)  # both real communities
    # RocketLab (42k subs, 40 posts/7d) outranks RKLB (15k, 12) on the metrics.
    assert result.subreddits[0].info.name == "RocketLab"
    assert result.flag is None


def test_discover_flags_when_nothing_found():
    with patch("core.social_media.reddit.arctic_shift_client.search_subreddits", return_value=[]), \
         patch("core.social_media.reddit.arctic_shift_client.count_posts_in_window", return_value=0):
        result = discover("ZZZZ", company_name=None, sleep=False)

    assert result.subreddits == []
    assert result.found is False
    assert result.flag == "no matching subreddit found"
