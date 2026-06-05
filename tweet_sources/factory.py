"""Factory for creating TweetSource instances from config."""

from __future__ import annotations

import os

from .base import TweetSource
from .getxapi import GetXApiSource
from .twitterapi import TwitterApiIoSource


def get_source(provider: str) -> TweetSource:
    """
    Return a TweetSource for *provider*.

    Reads credentials from environment variables:
      - getxapi   → GETXAPI_KEY
      - twitterapi → TWITTERAPI_IO_KEY
    """
    if provider == "getxapi":
        key = os.environ.get("GETXAPI_KEY", "").strip()
        if not key:
            raise EnvironmentError("GETXAPI_KEY is not set")
        return GetXApiSource(key)
    elif provider == "twitterapi":
        key = os.environ.get("TWITTERAPI_IO_KEY", "").strip()
        if not key:
            raise EnvironmentError("TWITTERAPI_IO_KEY is not set")
        return TwitterApiIoSource(key)
    else:
        raise ValueError(f"Unknown provider '{provider}'. Choose: getxapi | twitterapi")
