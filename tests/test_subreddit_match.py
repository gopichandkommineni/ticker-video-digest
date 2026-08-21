"""Unit tests for prefix-based subreddit matching — no real network calls.

The rejection cases are not hypothetical: every one is a subreddit the previous
guess-based pipeline actually selected and wrote to config/ticker_subreddits.yaml.
"""
from unittest.mock import patch

from core.social_media.reddit import subreddit_match as sm
from core.social_media.reddit.subreddit_match import (
    SubredditMetrics,
    company_words,
    match,
    name_is_about,
    prefix_stems,
    relevance,
    score,
)


def _sub(name: str, subscribers: int = 500, description: str = "",
         title: str = "", **kwargs) -> SubredditMetrics:
    return SubredditMetrics(name=name, subscribers=subscribers,
                            public_description=description, title=title, **kwargs)


# ---------------------------------------------------------------------------
# Prefix stems
# ---------------------------------------------------------------------------

def test_prefix_stems_include_ticker_and_company_forms():
    stems = prefix_stems("RKLB", "Rocket Lab Corporation")
    assert "rklb" in stems           # finds r/RKLB
    assert "rocket" in stems         # finds r/RocketLab
    assert "rocketlab" in stems


def test_prefix_stems_first_word_survives_punctuated_names():
    """r/NuSCALE_POWER is found by 'nuscale' but NOT by the joined 'nuscalepower'
    — prefix matching is literal, so the first-word stem is what rescues it."""
    stems = prefix_stems("SMR", "NuScale Power Corporation")
    assert "nuscale" in stems


def test_prefix_stems_dedupes_and_drops_empties():
    assert prefix_stems(None, None) == []
    stems = prefix_stems("FN", "FN")
    assert stems == ["fn"]


def test_company_words_strips_legal_suffixes():
    assert company_words("Rocket Lab Corporation") == ["rocket", "lab"]
    assert company_words("IonQ, Inc.") == ["ionq"]


# ---------------------------------------------------------------------------
# Name matching — the substring bug
# ---------------------------------------------------------------------------

def test_name_is_about_exact_and_suffixed():
    assert name_is_about("RKLB", "rklb")
    assert name_is_about("RKLBInvestors", "rklb")
    assert name_is_about("RocketLab", "rocketlab")


def test_name_is_about_rejects_bare_substrings():
    """Substring matching is what mapped MU->r/Microneedling, INTU->r/intuitiveeating
    and MRVL->r/MarvelLegends. A prefix must end on a known finance suffix."""
    assert not name_is_about("Microneedling", "micron")
    assert not name_is_about("intuitiveeating", "intuit")
    assert not name_is_about("MarvelLegends", "marvell")
    assert not name_is_about("pathofexile", "path")


# ---------------------------------------------------------------------------
# Relevance
# ---------------------------------------------------------------------------

def test_relevance_full_confidence_needs_name_and_description():
    rel, why = relevance(_sub("RKLB", 31845, "Rocket Lab (RKLB)"), "RKLB", "Rocket Lab Corporation")
    assert rel == 1.0
    assert "name is the ticker" in why


def test_relevance_name_alone_is_not_enough():
    """r/PATH is named exactly like the ticker and is a train enthusiasts' sub."""
    rel, _ = relevance(_sub("PATH", 195, ""), "PATH", "UiPath, Inc.")
    assert rel < 0.6


def test_relevance_rejects_unrelated_sub_with_matching_name():
    """r/sndk is Russian-language and nothing to do with SanDisk."""
    rel, _ = relevance(_sub("sndk", 6, "Сундучный сабреддит"), "SNDK", "Sandisk Corporation")
    assert rel < 0.6


def test_share_is_not_finance_vocabulary():
    """'A community to share and discuss news' is ordinary English. Counting
    'share' as finance context scored r/dellxps13 a perfect relevance for DELL."""
    rel, _ = relevance(
        _sub("dellxps13", 873, "A community to share and discuss news, updates and issues"),
        "DELL", "Dell Technologies Inc.",
    )
    assert rel < 0.6


def test_company_named_sub_needs_more_than_its_own_name():
    """"Fan-run subreddit for Rocket Lab" only repeats the name the sub is
    already called — circular, so it cannot reach selection on its own."""
    rel, why = relevance(
        _sub("RocketLab", 29422, "Fan-run subreddit for Rocket Lab, the end-to-end space company"),
        "RKLB", "Rocket Lab Corporation",
    )
    assert rel < 0.6
    assert "name is the company" in why


def test_company_named_sub_kept_when_it_names_the_ticker():
    """r/ASTSpaceMobile says "NASDAQ: ASTS" — independent evidence, so it stays.
    A size rule rejected this 28k-member sub, the best ASTS community there is."""
    rel, _ = relevance(
        _sub("ASTSpaceMobile", 28257,
             "AST SpaceMobile Inc. (NASDAQ: ASTS) is building the first space-based network"),
        "ASTS", "AST SpaceMobile, Inc.",
    )
    assert rel >= 0.6


def test_company_named_sub_kept_when_it_is_finance_flavoured():
    rel, _ = relevance(_sub("RocketLab_Stock", 818, "A bear-bull / TA sub for the stock"),
                       "RKLB", "Rocket Lab Corporation")
    assert rel >= 0.6


# ---------------------------------------------------------------------------
# Selection
# ---------------------------------------------------------------------------

def test_generic_giant_is_rejected():
    """r/QuantumComputing (64k, academic) is the biggest hit for QUBT and is not
    its community. The tell is scale relative to every other candidate."""
    giant = _sub("QuantumComputing", 64190,
                 "Academic discussion of all things quantum computing")
    real = _sub("qubt_stock", 1245, "The unofficial $QUBT Quantum Computing Inc. community")
    result = score(giant, "QUBT", "Quantum Computing Inc.", [giant, real])
    assert not result.selected


def test_ticker_named_sub_is_never_a_generic_giant():
    big = _sub("RKLB", 31845, "Rocket Lab (RKLB)")
    small = _sub("RKLBInvestors", 100, "Research on Rocket Lab")
    assert score(big, "RKLB", "Rocket Lab Corporation", [big, small]).selected


def test_dead_tiny_sub_is_rejected():
    tiny = _sub("avav", 3, "avavavavavavav")
    assert not score(tiny, "AVAV", "AeroVironment, Inc.", [tiny]).selected


def test_activity_outranks_size():
    """r/irenstocks reports 5 members but has dozens of weekly posters, while big
    dormant subs have none — the ranking must not be driven by member count."""
    active = _sub("irenstocks", 5, "The #1 IREN community. IREN Limited stock discussion")
    active.posts_7d, active.unique_commenters = 62, 44
    dormant = _sub("IRENstock", 1500, "IREN Limited stock")
    scored = sorted(
        [score(active, "IREN", "IREN Limited", [active, dormant]),
         score(dormant, "IREN", "IREN Limited", [active, dormant])],
        key=lambda c: -c.score,
    )
    assert scored[0].metrics.name == "irenstocks"


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def _prefix_stub(hits: dict[str, list[dict]]):
    """search_by_prefix returns (hits, reachable) — the stub must match."""
    return lambda prefix, limit=500: (hits.get(prefix, []), True)


def test_match_end_to_end_picks_the_company_sub():
    hits = {
        "rklb": [{"display_name": "RKLB", "subscribers": 31845,
                  "public_description": "Rocket Lab (RKLB)"}],
        "rocket": [{"display_name": "RocketLab", "subscribers": 29422,
                    "public_description": "Fan-run subreddit for Rocket Lab"},
                   {"display_name": "rocketry", "subscribers": 180000,
                    "public_description": "Amateur rocketry"}],
        "rocketlab": [],
    }
    with patch.object(sm, "search_by_prefix", _prefix_stub(hits)), \
         patch.object(sm, "count_posts", return_value=(46, False)), \
         patch.object(sm, "sample_commenters", return_value=(300, 120, True)), \
         patch.object(sm.time, "sleep"):
        result = match("rocket lab", ticker="RKLB", company_name="Rocket Lab Corporation")

    assert result.best is not None
    assert result.best.metrics.name in {"RKLB", "RocketLab"}
    assert "rocketry" not in [c.metrics.name for c in result.candidates]


def test_match_flags_when_nothing_corroborates():
    hits = {"path": [{"display_name": "pathofexile", "subscribers": 951224,
                      "public_description": "Discussion about Path of Exile, a free ARPG"}],
            "uipath": []}
    with patch.object(sm, "search_by_prefix", _prefix_stub(hits)), \
         patch.object(sm.time, "sleep"):
        result = match("PATH", ticker="PATH", company_name="UiPath, Inc.",
                       with_metrics=False)

    assert result.best is None
    assert result.flag is not None


def test_match_without_ticker_or_company_is_a_noop():
    result = match("???", ticker=None, company_name=None)
    assert result.candidates == []
    assert result.flag is not None


def test_unmeasured_candidates_are_flagged_as_such():
    """Only finalists get live metrics. An unmeasured candidate must not be
    reported as though its zero activity were an observation."""
    hits = {"rklb": [
        {"display_name": "RKLB", "subscribers": 31845,
         "public_description": "Rocket Lab (RKLB) stock discussion"},
        {"display_name": "RKLBInvestors", "subscribers": 1967,
         "public_description": "Research on Rocket Lab (RKLB) for investors"},
    ]}
    with patch.object(sm, "search_by_prefix", _prefix_stub(hits)), \
         patch.object(sm, "count_posts", return_value=(43, False)), \
         patch.object(sm, "sample_commenters", return_value=(300, 147, True)), \
         patch.object(sm.time, "sleep"):
        result = match("RKLB", ticker="RKLB", company_name="Rocket Lab Corporation",
                       finalists=1)

    by_name = {c.metrics.name: c.metrics for c in result.candidates}
    assert by_name["RKLB"].measured is True
    assert by_name["RKLBInvestors"].measured is False
    assert by_name["RKLBInvestors"].posts_7d == 0        # never looked at


def test_academic_topic_sub_is_rejected_however_large():
    giant = _sub("QuantumComputing", 64190, "Academic discussion of quantum computing")
    anchor = _sub("qubt_stock", 1245, "The unofficial $QUBT community")
    assert not score(giant, "QUBT", "Quantum Computing Inc.", [giant, anchor]).selected


def test_size_alone_never_decides():
    """Size cannot separate a topic sub from a real one: r/ASTSpaceMobile is 18x
    r/ASTS and genuine, r/QuantumComputing is 51x r/qubt_stock and is not. Both
    are big; only the description tells them apart."""
    asts = _sub("ASTSpaceMobile", 28257, "AST SpaceMobile Inc. (NASDAQ: ASTS)")
    asts_anchor = _sub("ASTS", 1590, "AST SpaceMobile discussion")
    assert score(asts, "ASTS", "AST SpaceMobile, Inc.", [asts, asts_anchor]).selected


def test_lone_ticker_named_candidate_survives():
    """r/CCJ is the only candidate for Cameco. A ticker-named sub describing the
    company is two independent facts, not circular evidence."""
    lone = _sub("CCJ", 183, "The world's largest publicly traded uranium company, Cameco")
    assert score(lone, "CCJ", "Cameco Corporation", [lone]).selected


def test_common_word_ticker_needs_dollar_form():
    """'path' appears in every Path of Exile description, and 'trades' reads as
    finance vocabulary — together they matched r/PathofExileTrades to PATH."""
    poe = _sub("PathofExileTrades", 1404, "Trading forum for Path of Exile items")
    rel, _ = relevance(poe, "PATH", "UiPath, Inc.")
    assert rel < 0.6
    real = _sub("PATH_Stock", 124, "UiPath the stock — $PATH discussion")
    assert relevance(real, "PATH", "UiPath, Inc.")[0] >= 0.6


def test_unreachable_archive_is_not_reported_as_no_match():
    """A throttled search returns [] just like a genuinely empty one. Recording
    the former as "this ticker has no subreddit" is how r/CCJ was lost."""
    with patch.object(sm, "search_by_prefix", lambda prefix, limit=500: ([], False)), \
         patch.object(sm.time, "sleep"):
        result = match("CCJ", ticker="CCJ", company_name="Cameco Corporation")
    assert result.archive_ok is False
    assert "unreachable" in result.flag


def test_empty_archive_result_is_reported_as_no_match():
    with patch.object(sm, "search_by_prefix", lambda prefix, limit=500: ([], True)), \
         patch.object(sm.time, "sleep"):
        result = match("ZZZZ", ticker="ZZZZ", company_name="Nonexistent Corp")
    assert result.archive_ok is True
    assert "no subreddit found" in result.flag


def test_overlong_prefix_is_dropped():
    """Subreddit names cap at 21 chars, and the archive answers a longer prefix
    with HTTP 400 — which the retry loop then misread as an unreachable archive
    and lost the whole ticker (REMX)."""
    stems = prefix_stems("REMX", "VanEck Rare Earth and Strategic Metals ETF")
    assert "remx" in stems
    assert "vaneck" in stems
    assert all(len(s) <= 21 for s in stems)


def test_rejected_prefix_does_not_mean_archive_is_down():
    with patch.object(sm, "search_by_prefix", lambda prefix, limit=500: ([], True)), \
         patch.object(sm.time, "sleep"):
        result = match("REMX", ticker="REMX", company_name="VanEck Rare Earth ETF")
    assert result.archive_ok is True


def test_ticker_named_sub_echoing_itself_is_rejected():
    """r/Poet is called "poet" and titled "poet"; r/avav is described
    "avavavavavav". Repeating the ticker adds no evidence."""
    assert relevance(_sub("Poet", 1752, "", title="poet"), "POET",
                     "POET Technologies Inc.")[0] < 0.6
    assert relevance(_sub("avav", 60, "avavavavavavavavav", title="avav"), "AVAV",
                     "AeroVironment, Inc.")[0] < 0.6


def test_ticker_named_sub_naming_the_company_is_kept():
    """The contrast case: r/CCJ names Cameco, r/RKLB names Rocket Lab."""
    assert relevance(
        _sub("CCJ", 183, "The world's largest publicly traded uranium company, Cameco"),
        "CCJ", "Cameco Corporation")[0] >= 0.6
    assert relevance(_sub("RKLB", 31845, "Rocket Lab (RKLB)"), "RKLB",
                     "Rocket Lab Corporation")[0] >= 0.6


def test_non_english_sub_needs_explicit_company_evidence():
    """r/sndk ("Сундучный сабреддит") is a Russian sub, not SanDisk."""
    ru = _sub("sndk", 6, "Сундучный сабреддит", title="sndk", lang="ru")
    assert relevance(ru, "SNDK", "Sandisk Corporation")[0] < 0.6


def test_common_word_ticker_needs_exact_name_match():
    """"coin" + "trader" parses as ticker+finance-suffix, which turned a generic
    crypto sub into Coinbase's community."""
    assert relevance(_sub("cointrader", 85, "Trading of cryptocurrencies, aka. coins."),
                     "COIN", "Coinbase Global, Inc.")[0] < 0.6


def test_dollar_ticker_does_not_match_a_longer_ticker():
    """"$pl" is a substring of "$PLTR" and "$mu" of "$MULN" — without a word
    boundary, PL matched Palantir's sub and MU matched Mullen's."""
    pltr = _sub("PLTR", 93842, "Palantir Technologies Inc. ($PLTR) Stock discussion")
    assert relevance(pltr, "PL", "Planet Labs PBC")[0] < 0.6
    muln = _sub("MULN_Automotive", 5000, "Mullen Automotive ($MULN) stock investors")
    assert relevance(muln, "MU", "Micron Technology, Inc.")[0] < 0.6


def test_dictionary_word_ticker_does_not_match_another_company():
    """r/Liteaccess is Lite Access Technologies (LTE.V), not Lumentum (LITE)."""
    lite = _sub("Liteaccess", 300,
                "LTE.V holders for discussions and news around Lite Access Technologies")
    assert relevance(lite, "LITE", "Lumentum Holdings Inc.")[0] < 0.6


def test_genuine_subs_with_odd_names_survive():
    """Judge the description, not the name: r/ASTSwingers is swing traders and
    r/WulfDen is TeraWulf's community — both real."""
    swing = _sub("ASTSwingers", 78, "We've seen the pump and dumps",
                 title="A sub for AST Spacemobile swing and day traders")
    assert relevance(swing, "ASTS", "AST SpaceMobile, Inc.")[0] >= 0.6
    wulf = _sub("WulfDen", 320, "TeraWulf Stock Community (WULF)", title="WulfDen")
    assert relevance(wulf, "WULF", "TeraWulf Inc.")[0] >= 0.6
