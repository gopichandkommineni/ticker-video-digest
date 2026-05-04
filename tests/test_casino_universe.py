from casino_dashboard.universe import load_universe


def test_sector_count():
    universe = load_universe()
    assert len(universe.sectors) == 8


def test_unique_ticker_count():
    universe = load_universe()
    tickers = universe.all_tickers()
    assert 50 <= len(tickers) <= 60, f"Expected ~55 unique tickers, got {len(tickers)}"


def test_all_tickers_deduped():
    universe = load_universe()
    tickers = universe.all_tickers()
    assert isinstance(tickers, set)
    # RKLB appears in drones_defense + space; must appear exactly once
    assert "RKLB" in tickers


def test_rklb_in_two_sectors():
    universe = load_universe()
    sectors = universe.sectors_for("RKLB")
    assert len(sectors) == 2
    assert "space" in sectors
    assert "drones_defense" in sectors


def test_sectors_for_single_sector_ticker():
    universe = load_universe()
    # IONQ is only in quantum
    sectors = universe.sectors_for("IONQ")
    assert sectors == ["quantum"]


def test_sectors_for_unknown_ticker():
    universe = load_universe()
    assert universe.sectors_for("FAKEXYZ") == []


def test_sector_fields():
    universe = load_universe()
    space = universe.sectors["space"]
    assert space.id == "space"
    assert space.display_name
    assert space.description
    assert space.stage  # non-empty string
    assert isinstance(space.speculative, bool)
    assert len(space.tickers) > 0


def test_every_sector_has_tickers():
    universe = load_universe()
    for sector_id, sector in universe.sectors.items():
        assert len(sector.tickers) > 0, f"Sector {sector_id} has no tickers"
