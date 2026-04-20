"""Smoke test: verify the package imports and version is set."""
import ticker_digest


def test_version() -> None:
    assert ticker_digest.__version__ == "0.1.0"
