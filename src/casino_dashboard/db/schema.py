import sqlite3
from pathlib import Path

_DEFAULT_DB_PATH = Path("data/snapshots.db")


def init_db(db_path: Path = _DEFAULT_DB_PATH) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.executescript("""
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

            CREATE TABLE IF NOT EXISTS signals (
                ticker       TEXT NOT NULL,
                date         TEXT NOT NULL,
                signal_name  TEXT NOT NULL,
                value        REAL,
                PRIMARY KEY (ticker, date, signal_name)
            );

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
        """)
        # Migrate existing DBs that predate notes/tags columns
        for col in ("notes", "tags"):
            try:
                conn.execute(f"ALTER TABLE manual_notes ADD COLUMN {col} TEXT")
            except Exception:
                pass  # column already exists

        # Migrate existing DBs that predate analyst high/low/count columns
        for col in (
            "analyst_target_high REAL",
            "analyst_target_low REAL",
            "analyst_count REAL",
        ):
            try:
                conn.execute(f"ALTER TABLE ticker_metadata ADD COLUMN {col}")
            except Exception:
                pass  # column already exists
