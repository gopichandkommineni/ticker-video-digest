"""Tests for the casino_mcp read-only query layer and server registration.

All tests run against fixture SQLite databases built in tmp_path — no
network, no production data. The snapshots fixture reuses the real
casino_dashboard.db.schema.init_db so the fixture schema cannot drift from
production; the fintwit fixture mirrors the fintwit-daily pipeline's schema.
"""
import sqlite3
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from casino_dashboard.db.schema import init_db
from casino_mcp import queries

TODAY = date.today()


@pytest.fixture
def themes_yaml(tmp_path: Path) -> Path:
    path = tmp_path / "themes.yaml"
    path.write_text(
        """
sectors:
  space:
    display_name: "Space"
    description: "test"
    stage: "mid"
    speculative: true
    tickers: [RKLB, ASTS]
  nuclear:
    display_name: "Nuclear"
    description: "test"
    stage: "mid"
    speculative: false
    tickers: [OKLO]
"""
    )
    return path


@pytest.fixture
def snapshots_db(tmp_path: Path) -> Path:
    db = tmp_path / "snapshots.db"
    init_db(db)
    with sqlite3.connect(db) as conn:
        conn.executemany(
            "INSERT INTO ticker_snapshots VALUES (?, ?, 10, 12, 9, 11, 11, 1000, 900.0)",
            [
                ("RKLB", "2026-07-01"),
                ("RKLB", "2026-07-02"),
                ("DEAD", "2026-01-15"),  # has rows but not in fixture universe
            ],
        )
        conn.execute(
            """INSERT INTO ticker_metadata
               (ticker, date, fifty_two_week_high, market_cap, next_earnings_date)
               VALUES ('RKLB', '2026-07-02', 15.5, 5e9, '2026-08-10')"""
        )
        conn.executemany(
            "INSERT INTO signals VALUES (?, ?, ?, ?)",
            [
                ("RKLB", "2026-07-01", "rsi_14", 55.0),
                ("RKLB", "2026-07-02", "rsi_14", 61.2),
                ("RKLB", "2026-07-02", "return_1m", 0.12),
            ],
        )
        conn.executemany(
            """INSERT INTO sector_heat
               (sector, date, agg_return_30d, constituent_count)
               VALUES (?, ?, ?, ?)""",
            [
                ("space", "2026-07-01", 0.05, 2),
                ("space", "2026-07-02", 0.08, 2),
                ("nuclear", "2026-07-02", -0.02, 1),
            ],
        )
        recent = (TODAY - timedelta(days=3)).isoformat()
        old = (TODAY - timedelta(days=400)).isoformat()
        conn.executemany(
            """INSERT INTO congress_trades
               (trade_id, bioguide_id, full_name, chamber, party, ticker,
                asset_type, transaction_type, transaction_date, disclosure_date,
                amount_low, amount_high, filing_id, fetched_at)
               VALUES (?, ?, ?, 'house', 'R', ?, 'stock', ?, ?, ?, 1000, 15000, ?, ?)""",
            [
                ("t1", "B001", "Jane Doe", "RKLB", "buy", recent, recent, "f1", recent),
                ("t2", "B002", "John Roe", "OKLO", "sell", recent, recent, "f2", recent),
                ("t3", "B001", "Jane Doe", "RKLB", "buy", old, old, "f3", old),
            ],
        )
        recent_dt = datetime.now(tz=timezone.utc) - timedelta(days=2)
        old_dt = datetime.now(tz=timezone.utc) - timedelta(days=60)
        conn.executemany(
            """INSERT INTO news_items
               (ticker, snap_date, title, link, publisher, published_at, fetched_at)
               VALUES (?, ?, ?, ?, 'TestWire', ?, ?)""",
            [
                ("RKLB", "2026-07-02", "Neutron update", "https://n/1",
                 recent_dt.isoformat(), recent_dt.isoformat()),
                ("RKLB", "2026-05-01", "Old story", "https://n/2",
                 old_dt.isoformat(), old_dt.isoformat()),
            ],
        )
    return db


@pytest.fixture
def fintwit_db(tmp_path: Path) -> Path:
    db = tmp_path / "fintwit.db"
    with sqlite3.connect(db) as conn:
        conn.executescript(
            """
            CREATE TABLE raw_tweets (
                tweet_id TEXT PRIMARY KEY, account_handle TEXT NOT NULL,
                text TEXT, created_at_utc TEXT NOT NULL, url TEXT,
                like_count INTEGER, retweet_count INTEGER, view_count INTEGER,
                is_deleted INTEGER DEFAULT 0
            );
            CREATE TABLE tweet_labels (
                tweet_id TEXT NOT NULL, label_type TEXT NOT NULL,
                label_value TEXT NOT NULL, classifier_version TEXT NOT NULL,
                confidence REAL, labeled_at TEXT NOT NULL,
                PRIMARY KEY (tweet_id, label_type, label_value, classifier_version)
            );
            """
        )
        recent = (datetime.now(tz=timezone.utc) - timedelta(days=1)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        stale = (datetime.now(tz=timezone.utc) - timedelta(days=90)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        conn.executemany(
            "INSERT INTO raw_tweets VALUES (?, ?, ?, ?, ?, 5, 1, 100, ?)",
            [
                ("101", "spacefan", "Big $RKLB launch window confirmed", recent,
                 "https://x.com/spacefan/status/101", 0),
                ("102", "nukebull", "Uranium supply squeeze thesis", recent,
                 "https://x.com/nukebull/status/102", 0),
                ("103", "spacefan", "$RKLB deleted take", recent,
                 "https://x.com/spacefan/status/103", 1),
                ("104", "spacefan", "$RKLB take from three months ago", stale,
                 "https://x.com/spacefan/status/104", 0),
                ("105", "quantguy", "Labeled rocket lab tweet, no cashtag", recent,
                 "https://x.com/quantguy/status/105", 0),
            ],
        )
        conn.execute(
            "INSERT INTO tweet_labels VALUES ('105', 'ticker', 'RKLB', 'regex-v1', 0.9, ?)",
            (recent,),
        )
    return db


# ── resolver ──────────────────────────────────────────────────────────────────


def test_resolve_ok(snapshots_db, themes_yaml):
    result = queries.resolve_ticker(
        "$rklb", snapshots_db=snapshots_db, themes_path=themes_yaml
    )
    assert result.status == "ok"
    assert result.ticker == "RKLB"
    assert result.sectors == ["space"]


def test_resolve_no_data_yet(snapshots_db, themes_yaml):
    result = queries.resolve_ticker(
        "ASTS", snapshots_db=snapshots_db, themes_path=themes_yaml
    )
    assert result.status == "no_data_yet"
    assert result.sectors == ["space"]


def test_resolve_not_in_universe(snapshots_db, themes_yaml):
    result = queries.resolve_ticker(
        "DEAD", snapshots_db=snapshots_db, themes_path=themes_yaml
    )
    assert result.status == "not_in_universe"


def test_resolve_unknown(snapshots_db, themes_yaml):
    result = queries.resolve_ticker(
        "ZZZZ", snapshots_db=snapshots_db, themes_path=themes_yaml
    )
    assert result.status == "unknown_ticker"
    assert result.ticker == "ZZZZ"


def test_resolve_merges_user_added_tickers(snapshots_db, themes_yaml):
    with sqlite3.connect(snapshots_db) as conn:
        conn.execute(
            """INSERT INTO user_added_tickers
               (ticker, theme_id, status, added_at)
               VALUES ('HSAI', 'space', 'complete', '2026-07-01T00:00:00Z')"""
        )
    result = queries.resolve_ticker(
        "HSAI", snapshots_db=snapshots_db, themes_path=themes_yaml
    )
    assert result.status == "no_data_yet"
    assert result.sectors == ["space"]


# ── snapshot / signals / sector heat ─────────────────────────────────────────


def test_get_snapshot_returns_latest_row_with_provenance(snapshots_db):
    result = queries.get_snapshot("rklb", snapshots_db=snapshots_db)
    assert result.snapshot is not None
    assert result.snapshot.date == "2026-07-02"
    assert result.snapshot.close == 11
    assert result.snapshot.provenance.table == "ticker_snapshots"
    assert result.snapshot.provenance.row_key == {"ticker": "RKLB", "date": "2026-07-02"}
    assert result.metadata is not None
    assert result.metadata.fifty_two_week_high == 15.5
    assert result.metadata.provenance.table == "ticker_metadata"


def test_get_snapshot_no_rows_returns_nulls(snapshots_db):
    result = queries.get_snapshot("ZZZZ", snapshots_db=snapshots_db)
    assert result.snapshot is None
    assert result.metadata is None


def test_get_signals_latest_date_only(snapshots_db):
    result = queries.get_signals("RKLB", snapshots_db=snapshots_db)
    assert result.date == "2026-07-02"
    assert {s.signal_name: s.value for s in result.signals} == {
        "rsi_14": 61.2,
        "return_1m": 0.12,
    }
    assert all(s.provenance.row_key["date"] == "2026-07-02" for s in result.signals)


def test_get_signals_empty(snapshots_db):
    result = queries.get_signals("ZZZZ", snapshots_db=snapshots_db)
    assert result.date is None
    assert result.signals == []


def test_get_sector_heat_latest_per_sector(snapshots_db):
    result = queries.get_sector_heat(snapshots_db=snapshots_db)
    by_sector = {r.sector: r for r in result.rows}
    assert set(by_sector) == {"space", "nuclear"}
    assert by_sector["space"].date == "2026-07-02"
    assert by_sector["space"].agg_return_30d == 0.08
    assert by_sector["space"].provenance.row_key == {
        "sector": "space", "date": "2026-07-02",
    }


def test_get_sector_heat_single_sector_filter(snapshots_db):
    result = queries.get_sector_heat("nuclear", snapshots_db=snapshots_db)
    assert [r.sector for r in result.rows] == ["nuclear"]


# ── fintwit search ────────────────────────────────────────────────────────────


def test_search_fintwit_by_text(fintwit_db):
    result = queries.search_fintwit(query="uranium", fintwit_db=fintwit_db)
    assert [t.tweet_id for t in result.rows] == ["102"]
    assert result.rows[0].provenance.db == "fintwit"
    assert result.rows[0].provenance.row_key["tweet_id"] == "102"
    assert result.rows[0].provenance.row_key["handle"] == "nukebull"


def test_search_fintwit_by_ticker_matches_cashtag_and_label(fintwit_db):
    result = queries.search_fintwit(ticker="rklb", fintwit_db=fintwit_db)
    ids = {t.tweet_id for t in result.rows}
    assert ids == {"101", "105"}  # cashtag match + label match
    assert "103" not in ids  # deleted excluded
    assert "104" not in ids  # outside 30-day window


def test_search_fintwit_by_handle_and_window(fintwit_db):
    result = queries.search_fintwit(handle="@SpaceFan", days=365, fintwit_db=fintwit_db)
    assert {t.tweet_id for t in result.rows} == {"101", "104"}


def test_search_fintwit_limit_and_truncated_flag(fintwit_db):
    result = queries.search_fintwit(handle="spacefan", days=365, limit=1,
                                    fintwit_db=fintwit_db)
    assert len(result.rows) == 1
    assert result.truncated is True


def test_search_fintwit_requires_a_filter(fintwit_db):
    with pytest.raises(ValueError):
        queries.search_fintwit(fintwit_db=fintwit_db)


# ── congress trades / news ────────────────────────────────────────────────────


def test_get_congress_trades_ticker_filter_and_window(snapshots_db):
    result = queries.get_congress_trades(ticker="RKLB", snapshots_db=snapshots_db)
    assert [t.trade_id for t in result.rows] == ["t1"]  # t3 outside 180d window
    assert result.rows[0].provenance.table == "congress_trades"
    assert result.rows[0].provenance.row_key["trade_id"] == "t1"


def test_get_congress_trades_member_substring(snapshots_db):
    result = queries.get_congress_trades(member="Roe", snapshots_db=snapshots_db)
    assert [t.full_name for t in result.rows] == ["John Roe"]


def test_get_news_window_and_provenance(snapshots_db):
    result = queries.get_news("RKLB", days=14, snapshots_db=snapshots_db)
    assert [n.title for n in result.rows] == ["Neutron update"]
    assert result.rows[0].provenance.row_key["link"] == "https://n/1"
    longer = queries.get_news("RKLB", days=90, snapshots_db=snapshots_db)
    assert [n.title for n in longer.rows] == ["Neutron update", "Old story"]


# ── read-only guarantee ───────────────────────────────────────────────────────


def test_connections_are_read_only(snapshots_db):
    conn = queries._ro_connect(snapshots_db)
    with pytest.raises(sqlite3.OperationalError, match="readonly"):
        conn.execute("INSERT INTO signals VALUES ('X', '2026-01-01', 's', 1.0)")
    conn.close()


def test_missing_db_raises_clean_error(tmp_path):
    with pytest.raises(FileNotFoundError):
        queries.get_snapshot("RKLB", snapshots_db=tmp_path / "nope.db")


# ── server registration ───────────────────────────────────────────────────────


def test_server_registers_all_seven_tools():
    import asyncio

    mcp_mod = pytest.importorskip("mcp")  # noqa: F841
    from casino_mcp.server import mcp

    tools = asyncio.run(mcp.list_tools())
    assert {t.name for t in tools} == {
        "resolve_ticker",
        "get_snapshot",
        "get_signals",
        "get_sector_heat",
        "search_fintwit",
        "get_congress_trades",
        "get_news",
    }
    assert all(t.outputSchema is not None for t in tools)
