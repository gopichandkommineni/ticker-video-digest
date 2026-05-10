"""Minimal FRED (St. Louis Fed) API wrapper.

Uses stdlib urllib to avoid an extra dependency. Returns a date-indexed
pandas Series of floats. Drops FRED's '.' missing-value marker.
"""
from __future__ import annotations

import json
import logging
from datetime import date
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd

from ticker_digest import config

log = logging.getLogger(__name__)

_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"


class FredUnavailable(RuntimeError):
    """Raised when FRED_API_KEY is not configured or is invalid."""


def fetch_series(series_id: str, start: date | None = None) -> pd.Series:
    if not config.FRED_API_KEY:
        raise FredUnavailable("FRED_API_KEY not configured")

    params = {
        "series_id": series_id,
        "api_key": config.FRED_API_KEY,
        "file_type": "json",
    }
    if start is not None:
        params["observation_start"] = start.isoformat()

    url = f"{_BASE_URL}?{urlencode(params)}"
    req = Request(url, headers={"User-Agent": "ticker-digest/0.1"})
    try:
        with urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        if exc.code == 400:
            raise FredUnavailable(
                f"FRED API key appears to be invalid (HTTP 400 for {series_id}). "
                "Check the key at https://fred.stlouisfed.org/docs/api/api_key.html"
            ) from exc
        raise

    obs = payload.get("observations", [])
    rows = [
        (pd.Timestamp(o["date"]), float(o["value"]))
        for o in obs
        if o.get("value") not in (None, "", ".")
    ]
    if not rows:
        return pd.Series(dtype=float)
    idx, vals = zip(*rows)
    return pd.Series(vals, index=pd.DatetimeIndex(idx), name=series_id, dtype=float)
