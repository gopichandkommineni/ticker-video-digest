"""The import surface other code depends on, pinned.

Pages, scripts, jobs and tests import names from a handful of modules. When
those modules get reorganised — as `db/repository.py` and `jobs/daily_refresh.py`
were — the names must keep resolving from the same place, or something breaks
somewhere nobody was looking.

These tests fail if a name disappears or changes shape. Deleting one on purpose
means deleting its line here in the same commit, which is the point: it becomes
a visible decision instead of an accident.
"""
from __future__ import annotations

import importlib
import inspect

import pytest

# Every name the dashboard imports from casino_dashboard.db.repository.
REPOSITORY_EXPORTS = [
    # snapshots
    "save_snapshot", "get_snapshot", "get_history",
    # signals
    "save_signal", "get_signals", "get_latest_signals_all_tickers",
    "get_signal_for_ticker_on_date", "get_latest_signal_for_tickers",
    "get_news_count_for_tickers",
    # social
    "save_social_mention", "get_social_history", "get_latest_social_mentions",
    "save_reddit_posts", "get_recent_reddit_posts",
    # metadata and notes
    "save_ticker_metadata", "get_latest_metadata_all_tickers", "save_manual_note",
    "save_user_annotations", "get_manual_notes_all_tickers",
    # sectors
    "save_etf_flow", "get_etf_flows", "save_sector_etf_mapping",
    "get_sector_etf_mapping", "save_deal_log_entries", "get_deal_log_for_sector",
    "get_deal_log_latest_date_per_sector", "save_sector_heat", "get_sector_heat_latest",
    # congress
    "upsert_congress_members", "upsert_congress_trades", "get_watched_members",
    "get_star_members", "get_recent_trades_for_members",
    # user-managed universe
    "add_user_ticker", "add_user_theme", "set_user_ticker_status",
    "remove_user_ticker", "get_user_added_tickers", "get_user_added_themes",
]

# Names that must stay importable from jobs.daily_refresh even though the
# implementations now live in refresh_sources / refresh_report.
DAILY_REFRESH_EXPORTS = [
    "main", "refresh_single_ticker", "_write_job_summary",
    "_refresh_apewisdom_by_subreddit", "_select_reddit_tickers",
    "_refresh_reddit_posts", "_refresh_congress",
]

# Entry points whose call shape other code relies on.
PINNED_SIGNATURES = {
    "casino_dashboard.jobs.daily_refresh:main": ["db_path"],
    "casino_dashboard.jobs.daily_refresh:refresh_single_ticker": ["ticker", "db_path"],
    "casino_dashboard.db.schema:init_db": ["db_path"],
    "casino_dashboard.universe:load_universe": ["path", "db_path"],
    "casino_dashboard.signals.orchestrator:compute_and_save_all_signals": [
        "universe", "db_path"],
}


@pytest.mark.parametrize("name", REPOSITORY_EXPORTS)
def test_repository_name_still_importable(name: str) -> None:
    module = importlib.import_module("casino_dashboard.db.repository")
    assert hasattr(module, name), (
        f"{name} is no longer importable from casino_dashboard.db.repository. "
        f"If that is deliberate, remove it from REPOSITORY_EXPORTS and from "
        f"the package's __all__ in the same commit."
    )
    assert callable(getattr(module, name))


def test_repository_all_matches_exports() -> None:
    """__all__ and this list must not drift apart."""
    module = importlib.import_module("casino_dashboard.db.repository")
    assert sorted(module.__all__) == sorted(REPOSITORY_EXPORTS)


@pytest.mark.parametrize("name", DAILY_REFRESH_EXPORTS)
def test_daily_refresh_name_still_importable(name: str) -> None:
    module = importlib.import_module("casino_dashboard.jobs.daily_refresh")
    assert hasattr(module, name), (
        f"{name} no longer resolves through casino_dashboard.jobs.daily_refresh. "
        f"Pages, scripts or tests import it from there — re-export it."
    )


@pytest.mark.parametrize("path,params", sorted(PINNED_SIGNATURES.items()))
def test_entry_point_signature_unchanged(path: str, params: list[str]) -> None:
    module_name, func_name = path.split(":")
    func = getattr(importlib.import_module(module_name), func_name)
    actual = list(inspect.signature(func).parameters)
    assert actual == params, (
        f"{path} now takes {actual}, was {params}. Callers outside this repo's "
        f"tests (workflows, the Streamlit pages) may pass these positionally."
    )


def test_page_imports_resolve() -> None:
    """Every module the Streamlit pages import must load without side effects."""
    for module_name in [
        "casino_dashboard.ui.loaders",
        "casino_dashboard.ui.sector_card",
        "casino_dashboard.ui.formatters",
        "casino_dashboard.ui.formatting",
        "casino_dashboard.ui.external_links",
        "casino_dashboard.ui.indicators",
        "casino_dashboard.ui.components.tile",
        "casino_dashboard.ui.components.sector_heat_table",
        "casino_dashboard.ui.components.tradingview",
        "casino_dashboard.data.ticker_validation",
        "casino_dashboard.universe",
        "core.market.reality_score",
        "core.market.thesis",
    ]:
        assert importlib.import_module(module_name) is not None
