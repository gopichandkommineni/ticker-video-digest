from pathlib import Path

import yaml
from pydantic import BaseModel

_THEMES_PATH = Path(__file__).parent.parent.parent / "config" / "themes.yaml"


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


def load_universe(path: Path = _THEMES_PATH) -> Universe:
    with open(path) as f:
        raw = yaml.safe_load(f)

    sectors: dict[str, Sector] = {}
    for sector_id, data in raw["sectors"].items():
        sectors[sector_id] = Sector(id=sector_id, **data)

    return Universe(sectors=sectors)
