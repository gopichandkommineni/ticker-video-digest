"""US congressional members, their committees, and their disclosed trades.

Split out of the original single repository.py — see that module's package
__init__ for the full map.
"""
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

from casino_dashboard.db.schema import _DEFAULT_DB_PATH
from casino_dashboard.models import CongressTrade


def upsert_congress_members(members: list[dict], db_path: Path = _DEFAULT_DB_PATH) -> None:
    """Upsert congress_members rows. members is a list of dicts with keys:
    bioguide_id, full_name, first_name, last_name, party, state, chamber,
    is_watched (int 0/1), is_star (int 0/1).

    Uses ON CONFLICT DO UPDATE so both is_watched and is_star flags are
    preserved when a member appears in both the committee list and the
    star-trader list (caller should pass both flags set on a merged dict).
    """
    updated_at = datetime.now(tz=timezone.utc).isoformat()
    with sqlite3.connect(db_path) as conn:
        for m in members:
            conn.execute(
                """
                INSERT INTO congress_members
                    (bioguide_id, full_name, first_name, last_name,
                     party, state, chamber, is_watched, is_star, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(bioguide_id) DO UPDATE SET
                    full_name  = excluded.full_name,
                    first_name = excluded.first_name,
                    last_name  = excluded.last_name,
                    party      = excluded.party,
                    state      = excluded.state,
                    chamber    = excluded.chamber,
                    is_watched = excluded.is_watched,
                    is_star    = excluded.is_star,
                    updated_at = excluded.updated_at
                """,
                (
                    m["bioguide_id"],
                    m.get("full_name", ""),
                    m.get("first_name", ""),
                    m.get("last_name", ""),
                    m.get("party", "I"),
                    m.get("state", ""),
                    m.get("chamber", ""),
                    int(m.get("is_watched", 0)),
                    int(m.get("is_star", 0)),
                    updated_at,
                ),
            )
            for comm in m.get("committees", []):
                conn.execute(
                    """
                    INSERT INTO congress_member_committees
                        (bioguide_id, committee_id, committee_name, title, rank)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(bioguide_id, committee_id) DO UPDATE SET
                        committee_name = excluded.committee_name,
                        title          = excluded.title,
                        rank           = excluded.rank
                    """,
                    (
                        m["bioguide_id"],
                        comm["committee_id"],
                        comm["committee_name"],
                        comm["title"],
                        comm.get("rank"),
                    ),
                )

def upsert_congress_trades(
    trades: list[CongressTrade], db_path: Path = _DEFAULT_DB_PATH
) -> None:
    """Upsert CongressTrade records. Idempotent via trade_id primary key."""
    fetched_at = datetime.now(tz=timezone.utc).isoformat()
    with sqlite3.connect(db_path) as conn:
        for t in trades:
            conn.execute(
                """
                INSERT INTO congress_trades (
                    trade_id, bioguide_id, full_name, chamber, party,
                    ticker, asset_type, transaction_type,
                    transaction_date, disclosure_date,
                    amount_low, amount_high, filing_id, fetched_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(trade_id) DO UPDATE SET
                    bioguide_id      = excluded.bioguide_id,
                    asset_type       = excluded.asset_type,
                    transaction_type = excluded.transaction_type,
                    amount_low       = excluded.amount_low,
                    amount_high      = excluded.amount_high,
                    filing_id        = excluded.filing_id,
                    fetched_at       = excluded.fetched_at
                """,
                (
                    t.trade_id,
                    t.bioguide_id,
                    t.full_name,
                    t.chamber,
                    t.party,
                    t.ticker,
                    t.asset_type,
                    t.transaction_type,
                    t.transaction_date.isoformat(),
                    t.disclosure_date.isoformat(),
                    t.amount_low,
                    t.amount_high,
                    t.filing_id,
                    fetched_at,
                ),
            )

def get_watched_members(db_path: Path = _DEFAULT_DB_PATH) -> pd.DataFrame:
    """Return DataFrame of congress_members where is_watched=1."""
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT bioguide_id, full_name, party, state, chamber,
                   is_watched, is_star
            FROM congress_members
            WHERE is_watched = 1
            ORDER BY last_name
            """
        ).fetchall()
    cols = ["bioguide_id", "full_name", "party", "state", "chamber", "is_watched", "is_star"]
    if not rows:
        return pd.DataFrame(columns=cols)
    return pd.DataFrame(rows, columns=cols)

def get_star_members(db_path: Path = _DEFAULT_DB_PATH) -> pd.DataFrame:
    """Return DataFrame of congress_members where is_star=1."""
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT bioguide_id, full_name, party, state, chamber,
                   is_watched, is_star
            FROM congress_members
            WHERE is_star = 1
            ORDER BY last_name
            """
        ).fetchall()
    cols = ["bioguide_id", "full_name", "party", "state", "chamber", "is_watched", "is_star"]
    if not rows:
        return pd.DataFrame(columns=cols)
    return pd.DataFrame(rows, columns=cols)

def get_recent_trades_for_members(
    bioguide_ids: list[str],
    days_back: int,
    db_path: Path = _DEFAULT_DB_PATH,
) -> pd.DataFrame:
    """Return congress_trades rows for the given members in the trailing days_back window.

    Sorted by disclosure_date DESC.
    """
    if not bioguide_ids:
        return pd.DataFrame()
    placeholders = ",".join("?" * len(bioguide_ids))
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            f"""
            SELECT
                ct.trade_id, ct.bioguide_id, ct.full_name, ct.chamber, ct.party,
                ct.ticker, ct.asset_type, ct.transaction_type,
                ct.transaction_date, ct.disclosure_date,
                ct.amount_low, ct.amount_high, ct.filing_id
            FROM congress_trades ct
            WHERE ct.bioguide_id IN ({placeholders})
              AND ct.disclosure_date >= date('now', ? || ' days')
            ORDER BY ct.disclosure_date DESC
            """,
            (*bioguide_ids, f"-{days_back}"),
        ).fetchall()
    cols = [
        "trade_id", "bioguide_id", "full_name", "chamber", "party",
        "ticker", "asset_type", "transaction_type",
        "transaction_date", "disclosure_date",
        "amount_low", "amount_high", "filing_id",
    ]
    if not rows:
        return pd.DataFrame(columns=cols)
    return pd.DataFrame(rows, columns=cols)
