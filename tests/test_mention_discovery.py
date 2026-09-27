"""Tests for finding subreddits from where a stock is discussed (fake archive, no network)."""
from datetime import datetime, timedelta, timezone

from core.social_media.reddit import arctic_shift_client as arctic
from core.social_media.reddit.mention_discovery import (
    Candidate,
    DiscoveryConfig,
    classify,
    discover,
    mentions_stock,
    name_matches,
)
from casino_dashboard.jobs import subreddit_find as job

NOW = datetime(2026, 9, 27, 12, 0, tzinfo=timezone.utc)
CFG = DiscoveryConfig()


def _p(sub, author, title="nothing to see", age_days=1.0, body=""):
    return {"subreddit": sub, "author": author, "title": title, "selftext": body,
            "created_utc": (NOW - timedelta(days=age_days)).timestamp()}


def _filler(sub, n, author="someone"):
    return [_p(sub, f"{author}{i}", title=f"other topic {i}") for i in range(n)]


class FakeFetch:
    def __init__(self, subs=None, authors=None, info=None, fail=()):
        self.subs, self.authors, self.info = subs or {}, authors or {}, info or {}
        self.fail = set(fail)
        self.calls = []

    def subreddit_posts(self, subreddit, after, cap):
        self.calls.append(("sub", subreddit))
        if subreddit in self.fail:
            return 422, []
        return 200, self.subs.get(subreddit, [])[:cap]

    def author_posts(self, author, after, cap):
        self.calls.append(("author", author))
        return 200, self.authors.get(author, [])[:cap]

    def subreddit_info(self, subreddit):
        return self.info.get(subreddit, {"subscribers": 1000})


def _rklb_world():
    return FakeFetch(
        subs={
            # Mapped: few posts repeat the ticker, but the name says RKLB.
            "RKLB": [_p("RKLB", "alice", "RKLB to the moon"), _p("RKLB", "bob", "RKLB Neutron"),
                     _p("RKLB", "alice", "Rocket Lab earnings")] + _filler("RKLB", 17),
            "wallstreetbets": [_p("wallstreetbets", "carol", "Rocket Lab calls"),
                               _p("wallstreetbets", "dave", "RKLB yolo"),
                               _p("wallstreetbets", "erin", "RKLB again")] + _filler("wallstreetbets", 97),
            # Found only through the authors.
            "RocketLab": [_p("RocketLab", a, "Rocket Lab launch") for a in ("alice", "bob", "zed")]
                         + [_p("RocketLab", "x", "RKLB news"), _p("RocketLab", "y", "Rocket Lab"),
                            _p("RocketLab", "z", "Rocket Lab")] + _filler("RocketLab", 4),
            "spacestocks": [_p("spacestocks", a, "RKLB vs ASTS") for a in ("alice", "q", "r", "s")]
                           + _filler("spacestocks", 36),
        },
        authors={
            "alice": [_p("RocketLab", "alice", "Rocket Lab launch"),
                      _p("spacestocks", "alice", "RKLB vs ASTS"),
                      _p("u_alice", "alice", "my RKLB thesis"),
                      _p("cooking", "alice", "soup")],
            "bob": [_p("RocketLab", "bob", "Rocket Lab launch")],
        },
    )


def _by_name(d):
    return {c.subreddit: c for c in d.candidates}


def test_follows_authors_and_classifies_by_share():
    fetch = _rklb_world()
    d = discover("RKLB", "Rocket Lab Corporation", ["RKLB"], ["wallstreetbets"],
                 fetch=fetch, cfg=CFG, now=NOW)
    c = _by_name(d)

    assert d.keywords == ["RKLB", "Rocket Lab"]
    assert d.seed_mentions == 6
    assert c["RocketLab"].verdict == "stock" and "authors" in c["RocketLab"].found_via
    assert not c["RocketLab"].mapped
    assert c["RKLB"].verdict == "stock"          # 15% share, but the name matches
    assert c["RKLB"].name_match and c["RKLB"].mapped
    assert c["spacestocks"].verdict == "general"  # 10%, no name match
    assert c["wallstreetbets"].verdict == "general"
    assert c["u_alice"].verdict == "excluded"
    assert "cooking" not in c                    # she never mentions it there
    assert d.candidates[0].verdict == "stock"    # stock first, then general, weak, excluded
    assert d.candidates[-1].verdict == "excluded"


def test_seed_listing_is_reused_not_reread():
    fetch = _rklb_world()
    discover("RKLB", "Rocket Lab Corporation", ["RKLB"], ["wallstreetbets"],
             fetch=fetch, cfg=CFG, now=NOW)
    assert fetch.calls.count(("sub", "RKLB")) == 1
    assert fetch.calls.count(("sub", "wallstreetbets")) == 1


def test_bots_and_deleted_are_not_followed():
    fetch = FakeFetch(subs={"RKLB": [_p("RKLB", "AutoModerator", "RKLB daily thread"),
                                     _p("RKLB", "[deleted]", "RKLB")]})
    d = discover("RKLB", None, ["RKLB"], [], fetch=fetch, cfg=CFG, now=NOW)
    assert d.authors_followed == 0
    assert not [call for call in fetch.calls if call[0] == "author"]


def test_noisy_ticker_needs_dollar_or_company():
    assert not mentions_stock({"title": "My PATH to recovery"}, "PATH", "UiPath, Inc.")
    assert mentions_stock({"title": "$PATH earnings"}, "PATH", "UiPath, Inc.")
    assert mentions_stock({"title": "UiPath beats"}, "PATH", "UiPath, Inc.")
    assert mentions_stock({"title": "RKLB up", "selftext": ""}, "RKLB", None)
    assert not mentions_stock({"title": "rklb lowercase"}, "RKLB", None)


def test_mapped_subreddit_without_evidence_is_weak():
    fetch = FakeFetch(subs={"PATH": [_p("PATH", f"u{i}", "my career PATH") for i in range(30)]})
    d = discover("PATH", "UiPath, Inc.", ["PATH"], [], fetch=fetch, cfg=CFG, now=NOW)
    c = _by_name(d)["PATH"]
    assert c.verdict == "weak" and c.mapped and not c.name_match
    assert "0 mention" in c.reason


def test_name_matches():
    assert name_matches("RKLBInvestors", "RKLB", None)
    assert name_matches("RocketLab_de", "RKLB", "Rocket Lab Corporation")
    assert not name_matches("PATH", "PATH", "UiPath, Inc.")      # everyday word: company only
    assert name_matches("UiPathStock", "PATH", "UiPath, Inc.")
    assert not name_matches("stocks", "RKLB", "Rocket Lab Corporation")


def test_classify_exclusions_and_thresholds():
    base = dict(subreddit="x", mentions=5, posts=10, share=0.5, authors=3)
    assert classify(Candidate(**base), {"over18": True}, CFG)[0] == "excluded"
    assert classify(Candidate(**base), {"quarantine": True}, CFG)[0] == "excluded"
    assert classify(Candidate(**{**base, "authors": 1}), None, CFG)[0] == "weak"
    assert classify(Candidate(**{**base, "share": 0.1}), None, CFG)[0] == "general"
    assert classify(Candidate(**{**base, "share": 0.1, "name_match": True}), None, CFG)[0] == "stock"
    assert classify(Candidate(**{**base, "posts": 0}), None, CFG)[0] == "weak"


def test_capped_listing_reports_days_covered():
    posts = [_p("RKLB", f"a{i % 5}", "RKLB", age_days=i * 0.01) for i in range(50)]
    fetch = FakeFetch(subs={"RKLB": posts})
    d = discover("RKLB", None, ["RKLB"], [], fetch=fetch,
                 cfg=DiscoveryConfig(listing_cap=50, max_authors=0), now=NOW)
    assert _by_name(d)["RKLB"].days_covered < 1


def test_failed_read_is_a_warning_not_a_crash():
    fetch = FakeFetch(subs={"RKLB": [_p("RKLB", "a", "RKLB")]}, fail={"wallstreetbets"})
    d = discover("RKLB", None, ["RKLB"], ["wallstreetbets"], fetch=fetch, cfg=CFG, now=NOW)
    assert sum("r/wallstreetbets" in w for w in d.warnings) == 1   # read once, failure remembered
    assert _by_name(d)["wallstreetbets"].verdict == "weak"


def test_author_filter_is_sent_as_a_plain_param():
    params = arctic._post_params(None, None, None, None, 100, "desc", "alice")
    assert params["author"] == "alice" and "query" not in params and "subreddit" not in params


def test_report_flags_new_and_unsupported():
    d = discover("RKLB", "Rocket Lab Corporation", ["RKLB", "deadsub"], ["wallstreetbets"],
                 fetch=_rklb_world(), cfg=CFG, now=NOW)
    text = "\n".join(job.render(d))
    assert "**Not in the map yet:** r/RocketLab" in text
    assert "r/deadsub (no posts read in the window)" in text
    assert "| r/u_alice | ✗ excluded |" in text
