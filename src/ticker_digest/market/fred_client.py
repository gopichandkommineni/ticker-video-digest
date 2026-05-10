"""Minimal FRED (St. Louis Fed) API wrapper.

Uses stdlib urllib to avoid an extra dependency. Returns a date-indexed
pandas Series of floats. Drops FRED's '.' missing-value marker.
"""
from __future__ import annotations

import json
import logging
import time
from datetime import date
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd

from ticker_digest import config

log = logging.getLogger(__name__)

_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"
_RETRY_DELAYS = (2, 4, 8)  # seconds between retries on transient errors


class FredUnavailable(RuntimeError):
    """Raised when FRED_API_KEY is not configured or is invalid."""


def _fetch_once(url: str) -> dict:
    req = Request(url, headers={"User-Agent": "ticker-digest/0.1"})
    try:
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        if exc.code in (400, 403):
            try:
                body = json.loads(exc.read().decode("utf-8"))
                fred_msg = body.get("error_message", exc.reason)
            except Exception:
                fred_msg = exc.reason
            raise FredUnavailable(
                f"FRED API error ({exc.code}) for {url.split('series_id=')[1].split('&')[0]}: {fred_msg}"
            ) from exc
        raise  # re-raise 5xx and others for retry logic


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
    last_exc: Exception | None = None
    for attempt, delay in enumerate((-1,) + _RETRY_DELAYS):
        if delay >= 0:
            log.debug("FRED %s: retrying after %ss (attempt %d)", series_id, delay, attempt)
            time.sleep(delay)
        try:
            payload = _fetch_once(url)
            break
        except FredUnavailable:
            raise  # 400/403 are permanent — don't retry
        except (HTTPError, URLError, OSError) as exc:
            log.warning("FRED %s transient error (will retry): %s", series_id, exc)
            last_exc = exc
    else:
        raise RuntimeError(f"FRED {series_id} failed after retries") from last_exc

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
