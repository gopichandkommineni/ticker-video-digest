# 03 — Ingestion contracts

## The adapter contract

Every source adapter implements one protocol. Nothing else in the system knows
whether bytes came from an RSS feed, a Greenhouse board, or my clipboard.

```python
class SourceAdapter(Protocol):
    name: str                      # "ats.greenhouse"
    kind: SourceKind               # jobs | blog | talk | oss | news | manual

    def validate(self, config: dict) -> None:
        """Raise ConfigError if this source's config is unusable.
        Called at load time so a typo fails fast, not at 2am."""

    def fetch(self, config: dict, ctx: FetchContext) -> Iterator[RawPayload]:
        """Yield raw payloads. May hit the network. Must respect
        ctx.rate_limiter and ctx.robots. Must not parse."""

    def normalize(self, raw: RawPayload) -> Iterator[NormalizedDocument]:
        """Pure. No network, no clock, no randomness. Given identical bytes,
        must return identical documents — this is what makes replay safe."""
```

`fetch` and `normalize` live in the same class because they share format
knowledge, but they are called by **different jobs at different times**.
`normalize` being pure is the load-bearing constraint: it lets a parser fix be
re-run across the entire raw store offline (ADR-0002).

`RawPayload` = `bytes` + `url` + `content_type` + `fetched_at` + `meta`.
The ingest job hashes, writes to `data/raw/`, and inserts `raw_document`.
Adapters never touch the database or the filesystem.

## Why ATS adapters, not company adapters

Nearly every large company outsources its job board to one of a handful of
applicant-tracking systems, and most of those expose a public JSON endpoint —
the same endpoint the company's own careers page calls from the browser. So
the adapter axis is the **platform**, and the company is configuration
(ADR-0004).

Planned adapters:

| Adapter | Platform | Shape |
|---|---|---|
| `ats.greenhouse` | Greenhouse | public board JSON, per-board slug |
| `ats.lever` | Lever | public postings JSON |
| `ats.ashby` | Ashby | public job-board API |
| `ats.smartrecruiters` | SmartRecruiters | public postings API |
| `ats.workday` | Workday | tenant + site, JSON POST search |
| `ats.eightfold` | Eightfold | JSON search endpoint |
| `careers.custom` | in-house boards | per-company config, last resort |
| `rss` | any feed | Atom/RSS, the blog workhorse |
| `manual.inbox` | me | see `docs/06-manual-intervention.md` |

Six ATS adapters plausibly cover most of a 40-company watchlist. The seventh,
`careers.custom`, is where in-house boards go — and where the config carries a
JSON path expression rather than code, so adding one is still not a new module.

> **Every endpoint in `config/sources.yaml` ships as `verified: false`.**
> These platforms change, and a plausible-looking URL that has been dead for a
> year is the worst possible failure: silent, and it looks like "they aren't
> hiring." The `career sources verify` command fetches each one, shows what
> came back, and only a human flips the flag. Unverified sources are ingested
> but excluded from analysis.

## Rate limiting and politeness

Enforced centrally in `FetchContext`, not per adapter, so a new adapter cannot
forget:

- **`robots.txt` is checked and honored** before any fetch; a disallowed path
  is skipped and logged, never quietly retried.
- **One request per second per host**, token-bucket, with jitter.
- **Descriptive User-Agent** with a contact address. Not a browser
  impersonation string.
- **Conditional requests**: `If-None-Match` / `If-Modified-Since` from the
  previous fetch. A 304 is a success that costs nothing.
- **Backoff**: on 429/503, exponential with `Retry-After` honored, three
  attempts, then mark the source failed for this run and move on.
- **No JS rendering, no headless browser, no CAPTCHA handling.** If a source
  needs those, it is not a source — it is a manual-inbox item
  (`docs/08-legal-and-etiquette.md`).

## Scheduling

Sources declare `refresh_interval_hours`; the ingest job selects what is due:

```sql
SELECT * FROM source
 WHERE enabled = 1
   AND (last_run_at IS NULL
        OR last_run_at < datetime('now', '-' || refresh_interval_hours || ' hours'));
```

Suggested cadences — job boards move faster than blogs, and both move slower
than people expect:

| Kind | Interval | Why |
|---|---|---|
| `jobs` | 24h | Postings appear and close on a daily rhythm. |
| `blog` | 72h | An engineering blog publishes weekly at best. |
| `oss` | 168h | Repo-level signal is slow. |
| `talk` | 168h | Conference-driven, bursty. |
| `manual` | on demand | Triggered by a file landing in the inbox. |

GitHub Actions runs the daily job (ADR-0010). Adding a source never edits the
workflow file.

## Failure semantics

Per-source isolation, always. The run ledger records one outcome per source:

| Outcome | Meaning | Action |
|---|---|---|
| `ok` | fetched, ≥1 payload | — |
| `not_modified` | 304 / identical hashes | — |
| `empty` | 200 but zero items | warn after 2 consecutive |
| `http_error` | 4xx/5xx after retries | warn after 2 consecutive |
| `parse_error` | fetched, normalize threw | **raw is still stored** — fix the parser and replay |
| `blocked` | robots.txt or 403 | disable, open a manual-inbox item |

Three consecutive non-`ok` runs auto-disable the source and add a pinned
annotation on the company, so it surfaces in the next brief. Silent decay is
the failure mode that actually kills tools like this.

## Adding a company: the intended experience

1. Add four lines to `config/companies.yaml`.
2. Find their board. Usually the careers page's network tab names the ATS.
3. Add sources to `config/sources.yaml`, `verified: false`.
4. `career sources verify --company <slug>` — inspect what came back.
5. Flip `verified: true` by hand.
6. `career ingest --company <slug> && career extract && career analyze`.

No Python written. If step 3 requires a new adapter, that is a signal worth
noticing — a genuinely new platform, not a one-off.
