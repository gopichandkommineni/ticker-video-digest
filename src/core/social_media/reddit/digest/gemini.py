"""Minimal Gemini client — one structured-JSON call, free-tier aware.

Why Gemini: the repository's free-LLM probes (research/probes/gemini_digest,
research/probes/groq_digest) ran the same batched summarisation job on both
free tiers. Groq's per-minute token bucket is emptied by one digest-sized
prompt. Gemini's limit is requests per day, and it differs by model: the probe
hit ~20/day on Flash (since the Dec-2025 cut), too few for 64 stocks, while
Flash-Lite allows several hundred a day.

Plain HTTPS + JSON (requests), no SDK: one endpoint, and the response schema
makes the model return JSON that parses. Free-tier limits are enforced by
Google per minute and per day; this client waits out a per-minute 429 using the
server's retry delay, and raises `QuotaExhausted` on a per-day one so the caller
can stop cleanly and pick up tomorrow.
"""
import json
import logging
import os
import re
import time

import requests

from core.social_media.reddit.digest.errors import (
    LLMError,
    LLMFatal,
    MissingKey,
    QuotaExhausted,
)

logger = logging.getLogger(__name__)

# Google's moving alias for the current Flash-Lite model. Flash-Lite, because
# the free tier gives full Flash only ~20 requests a day (64 stocks need 64). An
# alias, because a pinned version breaks the day Google retires it for new keys
# (gemini-2.5-flash already has). Override with REDDIT_DIGEST_MODEL.
DEFAULT_MODEL = "gemini-flash-lite-latest"
_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


# The shared digest errors, under the names this module has always used.
GeminiError = LLMError
GeminiFatal = LLMFatal


def _retry_delay(body: dict) -> float | None:
    """The server's suggested wait from a 429 body ('31s' → 31.0), if any."""
    for detail in (body.get("error") or {}).get("details") or []:
        delay = detail.get("retryDelay")
        if isinstance(delay, str):
            m = re.fullmatch(r"([\d.]+)s", delay.strip())
            if m:
                return float(m.group(1))
    return None


def _is_daily_quota(body: dict) -> bool:
    """True when the 429 names a per-day quota (not worth waiting for)."""
    text = json.dumps(body)
    return "PerDay" in text or "per day" in text.lower()


class GeminiClient:
    """generate_json(system, prompt, schema) → parsed dict."""

    # Free tier ≈ 10 requests a minute: the runner waits this long between calls.
    call_delay = 7.0

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float = 120.0,
        max_attempts: int = 4,
        max_wait: float = 90.0,
    ) -> None:
        self.api_key = api_key if api_key is not None else os.environ.get("GEMINI_API_KEY", "").strip()
        if not self.api_key:
            raise MissingKey("GEMINI_API_KEY is not set")
        self.model = model or os.environ.get("REDDIT_DIGEST_MODEL", "").strip() or DEFAULT_MODEL
        self.timeout = timeout
        self.max_attempts = max_attempts
        self.max_wait = max_wait

    def generate_json(self, system: str, prompt: str, schema: dict) -> dict:
        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": schema,
                "temperature": 0.2,
            },
        }
        url = _URL.format(model=self.model)
        headers = {"x-goog-api-key": self.api_key, "Content-Type": "application/json"}
        last = ""
        for attempt in range(1, self.max_attempts + 1):
            try:
                resp = requests.post(url, json=body, headers=headers, timeout=self.timeout)
            except requests.RequestException as exc:
                last = f"network error: {exc}"
                time.sleep(min(2 ** attempt, self.max_wait))
                continue

            if resp.status_code == 200:
                return self._parse(resp)

            try:
                err = resp.json()
            except ValueError:
                err = {}
            if resp.status_code == 429:
                if _is_daily_quota(err):
                    raise QuotaExhausted(f"{self.model}: daily free-tier quota used up")
                wait = min(_retry_delay(err) or 30.0, self.max_wait)
                logger.info("Gemini rate limit — waiting %.0fs (attempt %d)", wait, attempt)
                time.sleep(wait)
                last = "rate limited"
                continue
            if resp.status_code in (500, 502, 503, 504):
                last = f"HTTP {resp.status_code}"
                time.sleep(min(5 * attempt, self.max_wait))
                continue
            message = (err.get("error") or {}).get("message") or resp.text[:200]
            # Any other 4xx (400 bad key/request, 402 billing, 403, 404 model)
            # will fail identically for every stock.
            if 400 <= resp.status_code < 500:
                raise GeminiFatal(f"HTTP {resp.status_code}: {message}")
            raise GeminiError(f"HTTP {resp.status_code}: {message}")
        raise GeminiError(f"gave up after {self.max_attempts} attempts ({last})")

    @staticmethod
    def _parse(resp: requests.Response) -> dict:
        try:
            data = resp.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(text)
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            reason = ""
            try:
                reason = resp.json()["candidates"][0].get("finishReason", "")
            except Exception:  # noqa: BLE001 — best-effort diagnostics only
                pass
            raise GeminiError(f"unusable response {reason}: {exc}") from exc
