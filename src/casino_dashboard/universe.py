import logging
import sqlite3
from pathlib import Path

import yaml
from pydantic import BaseModel

_THEMES_PATH = Path(__file__).parent.parent.parent / "config" / "themes.yaml"
_DEFAULT_DB_PATH = Path("data/snapshots.db")

_logger = logging.getLogger(__name__)


class Sector(BaseModel):
    id: str
    display_name: str
    description: str
    stage: str
    speculative: bool
    tickers: list[str]


class Universe(BaseModel):
    sectors: dict[str, Sector]

    def all_tickers(self) -> set[str]:
        result: set[str] = set()
        for sector in self.sectors.values():
            result.update(sector.tickers)
        return result

    def sectors_for(self, ticker: str) -> list[str]:
        return [
            sector_id
            for sector_id, sector in self.sectors.items()
            if ticker in sector.tickers
        ]


def load_universe(
    path: Path = _THEMES_PATH,
    db_path: Path = _DEFAULT_DB_PATH,
) -> Universe:
    with open(path) as f:
        raw = yaml.safe_load(f)

    sectors: dict[str, Sector] = {}
    for sector_id, data in raw["sectors"].items():
        sectors[sector_id] = Sector(id=sector_id, **data)

    # Merge user_added_themes and user_added_tickers from the database.
    # Guards against (a) missing DB file, (b) tables not yet created.
    if db_path.exists():
        try:
            with sqlite3.connect(db_path) as conn:
                try:
                    theme_rows = conn.execute(
                        "SELECT theme_id, display_name, description, speculative "
                        "FROM user_added_themes"
                    ).fetchall()
                except sqlite3.OperationalError:
                    theme_rows = []

                # Only include tickers that have usable data (not 'failed').
                try:
                    ticker_rows = conn.execute(
                        "SELECT ticker, theme_id FROM user_added_tickers "
                        "WHERE status IN ('complete', 'pending')"
                    ).fetchall()
                except sqlite3.OperationalError:
                    ticker_rows = []
        except Exception as exc:
            _logger.debug("Could not read user tables from %s: %s", db_path, exc)
            theme_rows = []
            ticker_rows = []

        # Add user-defined themes that aren't already in the YAML.
        for theme_id, display_name, description, speculative in theme_rows:
            if theme_id not in sectors:
                sectors[theme_id] = Sector(
                    id=theme_id,
                    display_name=display_name,
                    description=description,
                    stage="user-added",
                    speculative=bool(speculative),
                    tickers=[],
                )

        # Append user-added tickers to their theme's ticker list.
        for ticker, theme_id in ticker_rows:
            if theme_id not in sectors:
                _logger.warning(
                    "user_added_ticker %r references unknown theme_id %r — skipping",
                    ticker,
                    theme_id,
                )
                continue
            if ticker not in sectors[theme_id].tickers:
                sectors[theme_id].tickers.append(ticker)

    return Universe(sectors=sectors)
