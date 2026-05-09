"""Test the `market` CLI subcommand."""
from datetime import datetime, timezone
from unittest.mock import MagicMock

from ticker_digest import cli
from ticker_digest.models import MarketIndicator, MarketSnapshot, RealityScore


def _snapshot() -> MarketSnapshot:
    return MarketSnapshot(
        generated_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
        indicators={
            "BUFFETT": MarketIndicator(
                name="Buffett",
                series_id="BUFFETT",
                source="computed",
                bucket="market",
                value=2.0,
                z_score=2.0,
            ),
            "T10Y2Y": MarketIndicator(
                name="10Y-2Y",
                series_id="T10Y2Y",
                source="fred",
                bucket="economy",
                value=-0.4,
                z_score=-1.5,
            ),
        },
    )


def _score() -> RealityScore:
    return RealityScore(
        score=1.7,
        band="severe_decoupling",
        market_z=2.0,
        economy_z=1.5,
        contributions={"BUFFETT": 2.0, "T10Y2Y": 1.5},
        used_indicators=["BUFFETT", "T10Y2Y"],
        skipped_indicators=[],
    )


def test_market_command_no_thesis(mocker, capsys):
    mocker.patch("ticker_digest.cli.get_snapshot", return_value=_snapshot())
    mocker.patch("ticker_digest.cli.compute_reality_score", return_value=_score())
    rc = cli.main(["market"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Reality Score: +1.70" in out
    assert "severe_decoupling" in out
    assert "BUFFETT" in out and "T10Y2Y" in out
    assert "Not investment advice" in out


def test_market_command_with_thesis(mocker, capsys):
    mocker.patch("ticker_digest.cli.get_snapshot", return_value=_snapshot())
    mocker.patch("ticker_digest.cli.compute_reality_score", return_value=_score())
    fake_thesis = MagicMock()
    fake_thesis.regime = "fragile"
    fake_thesis.narrative = "stretched markets, softening data"
    fake_thesis.bull_case = ["b1"]
    fake_thesis.bear_case = ["x1"]
    fake_thesis.key_watch_items = ["w1"]
    mocker.patch("ticker_digest.cli.generate_thesis", return_value=fake_thesis)
    rc = cli.main(["market", "--thesis"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Regime: fragile" in out
    assert "stretched markets" in out
    assert "Bull case" in out and "Bear case" in out


def test_ascii_bar_positive_and_negative():
    pos = cli._ascii_bar(1.5)
    neg = cli._ascii_bar(-1.5)
    assert "|" in pos and "|" in neg
    # Positive bar has bars to the right of the centerline
    assert pos.index("|") < pos.index("█")
    # Negative bar has bars to the left of the centerline
    assert neg.index("█") < neg.index("|")
