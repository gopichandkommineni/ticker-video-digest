"""Unit tests for subreddit discovery — no real network calls."""
import time
from unittest.mock import MagicMock, patch

from core.social_media.reddit import subreddit_discovery as sd
from core.social_media.reddit.subreddit_discovery import (
    SubredditInfo,
    _MIN_RELEVANCE_SELECT,
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


def test_substring_giants_rejected():
    # Regression: unanchored substring matching used to select these.
    # 'pl' must NOT match 'playstation'; 'intuit' must NOT match 'intuitiveeating'.
    ps = _info("playstation", 5_000_000, posts=100, desc="the playstation community")
    ps_scored = score_subreddit(ps, "PL", "Planet Labs")
    assert ps_scored.relevance == 0 and not ps_scored.selected

    eat = _info("intuitiveeating", 300_000, posts=100, desc="intuitive eating recovery")
    eat_scored = score_subreddit(eat, "INTU", "Intuit")
    assert eat_scored.relevance == 0 and not eat_scored.selected


def test_cross_contamination_rejected():
    # r/IntuitiveMachines is LUNR's community, not INTU's (Intuit).
    im = _info("IntuitiveMachines", 20_000, posts=30, desc="Intuitive Machines LUNR")
    assert not score_subreddit(im, "INTU", "Intuit").selected          # wrong stock
    assert score_subreddit(im, "LUNR", "Intuitive Machines").selected  # right stock


def test_name_form_and_suffix_match_selected():
    # Company-form name and ticker+suffix names are real matches.
    assert score_subreddit(_info("PlanetLabs", 3000, posts=5), "PL", "Planet Labs").selected
    assert score_subreddit(_info("MDASpaceInvestors", 1500, posts=5, desc="MDA Space"),
                           "MDA", "MDA Space").selected


def test_weak_partial_match_not_selected():
    # relevance 0.6 is the floor; below it can't select even if big + active.
    weak = _info("spacestocks", 50_000, posts=100, desc="general space stock chat")
    scored = score_subreddit(weak, "RKLB", "Rocket Lab")
    assert scored.relevance < _MIN_RELEVANCE_SELECT
    assert not scored.selected


def test_quarantined_not_selected():
    # Relevant + sized + active, so quarantine is the only thing rejecting it.
    info = _info("RKLBraw", 5000, posts=10, desc="RKLB stock discussion", quarantined=True)
    scored = score_subreddit(info, "RKLB", "Rocket Lab")
    assert scored.relevance >= _MIN_RELEVANCE_SELECT
    assert not scored.selected
    assert "quarantined" in scored.reasons


# ---------------------------------------------------------------------------
# Round-2 tuning: mention vs name matches, and the relaxed activity gate
# ---------------------------------------------------------------------------

def test_bare_mention_without_finance_context_rejected():
    # r/HPOmen (laptops) mentions "HP"; r/ETNmining (crypto) mentions "ETN";
    # r/coincollecting mentions "coin". A symbol as a coincidental word is not a
    # match unless the sub is finance-flavored.
    omen = _info("HPOmen", 120_000, posts=50, desc="HP Omen gaming laptops and desktops")
    assert score_subreddit(omen, "HP", "HP Inc").relevance == 0

    etn = _info("ETNmining", 8000, posts=30, desc="Electroneum ETN mining community")
    assert score_subreddit(etn, "ETN", "Eaton").relevance == 0


def test_common_word_ticker_needs_finance_context():
    # r/cake is baking. Even though the name equals the ticker, no finance
    # context => not the stock. A real $CAKE sub would talk stock.
    baking = _info("cake", 900_000, posts=100, desc="a subreddit for cakes and baking")
    assert score_subreddit(baking, "CAKE", "Cheesecake Factory").relevance == 0

    stock = _info("cake", 1500, posts=10, desc="Cheesecake Factory CAKE stock discussion")
    assert score_subreddit(stock, "CAKE", "Cheesecake Factory").selected


def test_bare_mention_with_finance_context_matches():
    info = _info("smallcapstocks", 4000, posts=20,
                 desc="deep dives on RKLB and other small-cap stocks")
    scored = score_subreddit(info, "RKLB", "Rocket Lab")
    assert scored.relevance >= _MIN_RELEVANCE_SELECT


def test_dormant_but_sized_investor_sub_selected():
    # r/IonQStock: 1837 members, 0 posts in the last 7d — real, just quiet.
    info = _info("IonQStock", 1837, posts=0, desc="IONQ investors")
    scored = score_subreddit(info, "IONQ", "IonQ")
    assert scored.selected


def test_small_but_active_new_sub_selected():
    # r/SNDK_Stock: 22 members, 100 posts (a days-old spin-off community).
    info = _info("SNDK_Stock", 22, posts=100, desc="SNDK SanDisk stock")
    scored = score_subreddit(info, "SNDK", "SanDisk")
    assert scored.selected


def test_one_person_sub_still_noise():
    # 3 members: below the active floor even with posts — one person talking.
    info = _info("MRVL_Stock", 3, posts=9, desc="MRVL stock")
    scored = score_subreddit(info, "MRVL", "Marvell")
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
    # Relevance multiplies the score, so the exact-ticker match (r/RKLB, rel 1.0)
    # ranks ahead of the larger name-only match (r/RocketLab, rel 0.6).
    assert result.subreddits[0].info.name == "RKLB"
    assert result.flag is None


def test_discover_flags_when_nothing_found():
    with patch("core.social_media.reddit.arctic_shift_client.search_subreddits", return_value=[]), \
         patch("core.social_media.reddit.arctic_shift_client.count_posts_in_window", return_value=0):
        result = discover("ZZZZ", company_name=None, sleep=False)

    assert result.subreddits == []
    assert result.found is False
    assert result.flag == "no matching subreddit found"
