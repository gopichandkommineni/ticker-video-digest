"""The only place the dashboard reads or writes `data/snapshots.db`.

This used to be one 1,132-line module. It is now one module per subject area,
and this file re-exports everything, so `from casino_dashboard.db.repository
import save_snapshot` works exactly as it always did.

Which file holds what:

| Module            | Subject                                                  |
|-------------------|----------------------------------------------------------|
| `snapshots.py`    | Daily OHLCV rows and their news items                     |
| `signals.py`      | Computed numbers: returns, RSI, distance from high/low    |
| `social.py`       | Reddit mention counts and the posts behind them           |
| `metadata.py`     | Company facts and hand-written notes                      |
| `sectors.py`      | ETF flows, the deal log, sector heat rollups              |
| `congress.py`     | Congressional members, committees, disclosed trades       |
| `user_universe.py`| Tickers/themes added through the Add Stocks page          |

Adding a query? Put it in the module that owns the subject, then add its name
to that section of `__all__` below.
"""
from casino_dashboard.db.repository.congress import (
    get_recent_trades_for_members,
    get_star_members,
    get_watched_members,
    upsert_congress_members,
    upsert_congress_trades,
)
from casino_dashboard.db.repository.metadata import (
    get_latest_metadata_all_tickers,
    get_manual_notes_all_tickers,
    save_manual_note,
    save_ticker_metadata,
    save_user_annotations,
)
from casino_dashboard.db.repository.sectors import (
    get_deal_log_for_sector,
    get_deal_log_latest_date_per_sector,
    get_etf_flows,
    get_sector_etf_mapping,
    get_sector_heat_latest,
    save_deal_log_entries,
    save_etf_flow,
    save_sector_etf_mapping,
    save_sector_heat,
)
from casino_dashboard.db.repository.signals import (
    get_latest_signal_for_tickers,
    get_latest_signals_all_tickers,
    get_news_count_for_tickers,
    get_signal_for_ticker_on_date,
    get_signals,
    save_signal,
)
from casino_dashboard.db.repository.snapshots import (
    get_history,
    get_snapshot,
    save_snapshot,
)
from casino_dashboard.db.repository.social import (
    get_latest_social_mentions,
    get_recent_reddit_posts,
    get_social_history,
    save_reddit_posts,
    save_social_mention,
)
from casino_dashboard.db.repository.user_universe import (
    add_user_theme,
    add_user_ticker,
    get_user_added_themes,
    get_user_added_tickers,
    remove_user_ticker,
    set_user_ticker_status,
)

__all__ = [
    # snapshots
    "save_snapshot",
    "get_snapshot",
    "get_history",
    # signals
    "save_signal",
    "get_signals",
    "get_latest_signals_all_tickers",
    "get_signal_for_ticker_on_date",
    "get_latest_signal_for_tickers",
    "get_news_count_for_tickers",
    # social
    "save_social_mention",
    "get_social_history",
    "get_latest_social_mentions",
    "save_reddit_posts",
    "get_recent_reddit_posts",
    # metadata and notes
    "save_ticker_metadata",
    "get_latest_metadata_all_tickers",
    "save_manual_note",
    "save_user_annotations",
    "get_manual_notes_all_tickers",
    # sectors
    "save_etf_flow",
    "get_etf_flows",
    "save_sector_etf_mapping",
    "get_sector_etf_mapping",
    "save_deal_log_entries",
    "get_deal_log_for_sector",
    "get_deal_log_latest_date_per_sector",
    "save_sector_heat",
    "get_sector_heat_latest",
    # congress
    "upsert_congress_members",
    "upsert_congress_trades",
    "get_watched_members",
    "get_star_members",
    "get_recent_trades_for_members",
    # user-managed universe
    "add_user_ticker",
    "add_user_theme",
    "set_user_ticker_status",
    "remove_user_ticker",
    "get_user_added_tickers",
    "get_user_added_themes",
]
