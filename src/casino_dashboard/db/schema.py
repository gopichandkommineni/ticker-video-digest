"""The shape of `data/snapshots.db` — every table, grouped by subject.

The DDL below mirrors the modules in `repository/`: one constant per subject,
in the same order. Adding a table means adding it to the matching constant
here and a query for it to the matching module there.

Everything is `IF NOT EXISTS`, so init_db() is safe on every run — and it is
called on every run, by both the daily job and the Add Stocks page.

The indentation inside each block is load-bearing in one narrow sense: SQLite
stores the literal CREATE text in sqlite_master, so reflowing it would make
freshly created databases differ from existing ones for no reason.
"""
import sqlite3
from pathlib import Path

_DEFAULT_DB_PATH = Path("data/snapshots.db")


# Daily OHLCV rows and the news items attached to them.
_SNAPSHOTS_DDL = """
            CREATE TABLE IF NOT EXISTS ticker_snapshots (
                ticker        TEXT    NOT NULL,
                date          TEXT    NOT NULL,
                open          REAL    NOT NULL,
                high          REAL    NOT NULL,
                low           REAL    NOT NULL,
                close         REAL    NOT NULL,
                adj_close     REAL    NOT NULL,
                volume        INTEGER NOT NULL,
                avg_volume_30d REAL,
                PRIMARY KEY (ticker, date)
            );

            CREATE TABLE IF NOT EXISTS news_items (
                id           INTEGER PRIMARY KEY,
                ticker       TEXT    NOT NULL,
                snap_date    TEXT    NOT NULL,
                title        TEXT    NOT NULL,
                link         TEXT    NOT NULL,
                publisher    TEXT    NOT NULL,
                published_at TEXT    NOT NULL,
                fetched_at   TEXT    NOT NULL
            );
"""


# Computed per-ticker numbers: returns, RSI, distance from high/low.
_SIGNALS_DDL = """
            CREATE TABLE IF NOT EXISTS signals (
                ticker       TEXT NOT NULL,
                date         TEXT NOT NULL,
                signal_name  TEXT NOT NULL,
                value        REAL,
                PRIMARY KEY (ticker, date, signal_name)
            );
"""


# Reddit mention counts and the posts behind them.
_SOCIAL_DDL = """
            -- subreddit defaults to '' (empty string, not NULL) for the
            -- apewisdom aggregate row so the PRIMARY KEY constraint works.
            CREATE TABLE IF NOT EXISTS social_mentions (
                ticker            TEXT    NOT NULL,
                date              TEXT    NOT NULL,
                source            TEXT    NOT NULL,
                mention_count     INTEGER NOT NULL,
                mentions_24h_ago  INTEGER,
                upvote_sum        INTEGER,
                subreddit         TEXT    NOT NULL DEFAULT '',
                PRIMARY KEY (ticker, date, source, subreddit)
            );

            -- Individual Reddit posts pulled by RedditScraper (public JSON API
            -- or PRAW). Unlike social_mentions (aggregate counts), this stores
            -- the post itself: title, body, score, comments — the raw material
            -- for future LLM extraction and richer momentum signals.
            -- Keyed on (post_id, ticker) because one post can surface under
            -- more than one ticker's search and we keep each association.
            CREATE TABLE IF NOT EXISTS reddit_posts (
                post_id       TEXT    NOT NULL,
                ticker        TEXT    NOT NULL,
                subreddit     TEXT    NOT NULL DEFAULT '',
                author        TEXT    NOT NULL DEFAULT '',
                title         TEXT    NOT NULL DEFAULT '',
                content       TEXT    NOT NULL DEFAULT '',
                url           TEXT    NOT NULL DEFAULT '',
                score         INTEGER NOT NULL DEFAULT 0,
                comment_count INTEGER NOT NULL DEFAULT 0,
                published_at  TEXT    NOT NULL,
                fetched_at    TEXT    NOT NULL,
                PRIMARY KEY (post_id, ticker)
            );

            CREATE INDEX IF NOT EXISTS idx_reddit_posts_ticker
                ON reddit_posts(ticker, published_at DESC);

            CREATE INDEX IF NOT EXISTS idx_reddit_posts_subreddit
                ON reddit_posts(subreddit, published_at DESC);
"""


# Company facts, plus the hand-written notes from config/manual_notes.yaml.
_METADATA_DDL = """
            CREATE TABLE IF NOT EXISTS ticker_metadata (
                ticker                  TEXT NOT NULL,
                date                    TEXT NOT NULL,
                fifty_two_week_high     REAL,
                fifty_two_week_low      REAL,
                short_pct_of_float      REAL,
                short_ratio_days        REAL,
                analyst_target_mean     REAL,
                analyst_target_high     REAL,
                analyst_target_low      REAL,
                analyst_count           REAL,
                held_pct_insiders       REAL,
                held_pct_institutions   REAL,
                market_cap              REAL,
                revenue_ttm             REAL,
                revenue_growth_yoy      REAL,
                profit_margin           REAL,
                beta                    REAL,
                next_earnings_date      TEXT,
                next_earnings_time      TEXT,
                last_earnings_date      TEXT,
                PRIMARY KEY (ticker, date)
            );

            CREATE TABLE IF NOT EXISTS manual_notes (
                ticker      TEXT NOT NULL,
                catalyst    TEXT,
                red_flag    TEXT,
                notes       TEXT,
                tags        TEXT,
                updated_at  TEXT NOT NULL,
                PRIMARY KEY (ticker)
            );
"""


# Theme-level data: ETF flows, the deal log, and sector heat rollups.
_SECTORS_DDL = """
            CREATE TABLE IF NOT EXISTS etf_flows (
                etf_ticker   TEXT NOT NULL,
                date         TEXT NOT NULL,
                net_flow_usd REAL,
                aum_usd      REAL,
                price        REAL,
                PRIMARY KEY (etf_ticker, date)
            );

            CREATE TABLE IF NOT EXISTS sector_etf_mapping (
                sector      TEXT    NOT NULL,
                etf_ticker  TEXT    NOT NULL,
                is_primary  INTEGER NOT NULL DEFAULT 1,
                PRIMARY KEY (sector, etf_ticker)
            );

            CREATE TABLE IF NOT EXISTS deal_log (
                deal_id        TEXT PRIMARY KEY,
                date           TEXT NOT NULL,
                sector         TEXT NOT NULL,
                amount_usd     REAL,
                deal_type      TEXT,
                primary_ticker TEXT,
                source_url     TEXT,
                summary        TEXT NOT NULL,
                loaded_at      TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sector_heat (
                sector                 TEXT NOT NULL,
                date                   TEXT NOT NULL,
                etf_flow_5d_30d_ratio  REAL,
                deal_log_30d_total_usd REAL,
                deal_log_30d_count     INTEGER,
                days_since_last_deal   INTEGER,
                agg_social_velocity    REAL,
                news_heat_ratio        REAL,
                agg_return_30d         REAL,
                pct_above_sma50        REAL,
                agg_atr_pct_change_30d REAL,
                constituent_count      INTEGER NOT NULL,
                PRIMARY KEY (sector, date)
            );
"""


# US congressional members, their committees, and their disclosed trades.
_CONGRESS_DDL = """
            CREATE TABLE IF NOT EXISTS congress_members (
                bioguide_id   TEXT PRIMARY KEY,
                full_name     TEXT NOT NULL,
                first_name    TEXT NOT NULL,
                last_name     TEXT NOT NULL,
                party         TEXT NOT NULL,
                state         TEXT NOT NULL,
                chamber       TEXT NOT NULL,
                is_watched    INTEGER NOT NULL DEFAULT 0,
                is_star       INTEGER NOT NULL DEFAULT 0,
                updated_at    TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS congress_member_committees (
                bioguide_id      TEXT NOT NULL,
                committee_id     TEXT NOT NULL,
                committee_name   TEXT NOT NULL,
                title            TEXT NOT NULL,
                rank             INTEGER,
                PRIMARY KEY (bioguide_id, committee_id)
            );

            CREATE TABLE IF NOT EXISTS congress_trades (
                trade_id          TEXT PRIMARY KEY,
                bioguide_id       TEXT,
                full_name         TEXT NOT NULL,
                chamber           TEXT NOT NULL,
                party             TEXT NOT NULL,
                ticker            TEXT NOT NULL,
                asset_type        TEXT,
                transaction_type  TEXT NOT NULL,
                transaction_date  TEXT NOT NULL,
                disclosure_date   TEXT NOT NULL,
                amount_low        REAL,
                amount_high       REAL,
                filing_id         TEXT,
                fetched_at        TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_congress_trades_disclosure
                ON congress_trades(disclosure_date DESC);

            CREATE INDEX IF NOT EXISTS idx_congress_trades_bioguide
                ON congress_trades(bioguide_id, disclosure_date DESC);

            CREATE INDEX IF NOT EXISTS idx_congress_trades_ticker
                ON congress_trades(ticker, disclosure_date DESC);
"""


# Tickers and themes added through the Add Stocks page.
_USER_UNIVERSE_DDL = """
            CREATE TABLE IF NOT EXISTS user_added_themes (
                theme_id       TEXT PRIMARY KEY,
                display_name   TEXT NOT NULL,
                description    TEXT NOT NULL,
                speculative    INTEGER NOT NULL DEFAULT 0,
                created_by     TEXT,
                created_at     TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS user_added_tickers (
                ticker         TEXT PRIMARY KEY,
                theme_id       TEXT NOT NULL,
                company_name   TEXT,
                status         TEXT NOT NULL DEFAULT 'pending',
                status_detail  TEXT,
                added_by       TEXT,
                added_at       TEXT NOT NULL,
                last_fetch_at  TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_user_tickers_status
              ON user_added_tickers(status);
"""


# Applied in this order on every run. The names match the repository/ modules.
_SCHEMA = (
    _SNAPSHOTS_DDL,
    _SIGNALS_DDL,
    _SOCIAL_DDL,
    _METADATA_DDL,
    _SECTORS_DDL,
    _CONGRESS_DDL,
    _USER_UNIVERSE_DDL,
)

# Columns added to tables that shipped before them. SQLite has no
# "ADD COLUMN IF NOT EXISTS", so on a database that already has the column
# the ALTER raises and we move on.
_ADDED_COLUMNS = (
    ("manual_notes", "notes TEXT"),
    ("manual_notes", "tags TEXT"),
    ("ticker_metadata", "analyst_target_high REAL"),
    ("ticker_metadata", "analyst_target_low REAL"),
    ("ticker_metadata", "analyst_count REAL"),
)


def _add_missing_columns(conn: sqlite3.Connection) -> None:
    """Bring a database created by an older version up to the current columns."""
    for table, column in _ADDED_COLUMNS:
        try:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column}")
        except Exception:
            pass  # column already exists


def init_db(db_path: Path = _DEFAULT_DB_PATH) -> None:
    """Create every table and index that does not exist yet. Idempotent."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        for ddl in _SCHEMA:
            conn.executescript(ddl)
        _add_missing_columns(conn)
