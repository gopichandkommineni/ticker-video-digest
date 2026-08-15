# Reddit data — local runbook

How to pull Reddit data: discover which subreddits belong to each stock, save
that map, and pull posts + mention signal into the database.

> **⚠️ Reddit closed the direct paths (2026).** Reddit shut down its public JSON
> API and put remaining access behind Cloudflare, so direct fetches — even
> browser-impersonated, even via residential proxy — are unreliable, and new API
> app creation is gated. The code therefore uses **managed data sources** that
> aren't subject to Reddit's block:
>
> - **Arctic Shift** (default, **free**) — the community archive API
>   (`arctic-shift.photon-reddit.com`). Powers subreddit discovery *and* full
>   post pulling. Not reddit.com, so no Cloudflare/IP block; works locally and in
>   CI. Tradeoff: ~1–2 day data lag, community uptime.
> - **Apify** (optional, paid) — managed scraper for **intraday-fresh** full
>   posts. Set `APIFY_TOKEN` and the pull uses it instead.
> - **ApeWisdom** (free) — aggregated mention counts + velocity, incl. a
>   per-subreddit breakdown, already wired into the daily refresh.
>
> The direct client (public JSON / PRAW / proxy) remains a fallback but is no
> longer reliable on its own — select it only with `REDDIT_BACKEND=direct`.

## 0. Choose a backend

The pull auto-selects: **`APIFY_TOKEN` set → Apify; else → Arctic Shift (free).**
Force one with `REDDIT_BACKEND=arctic_shift|apify|direct`.

- **Free, works today (recommended)** → set nothing. Arctic Shift powers
  discovery + posts; ApeWisdom runs in the daily refresh for live velocity.
- **Need this-week's posts** → add an [Apify](https://apify.com) token.

## 1. One-time setup

```bash
cd ticker-video-digest

# Python 3.11+ virtualenv
python3.11 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# Editable install — after this, `python -m casino_dashboard...` needs no PYTHONPATH
pip install -e ".[dev]"
```

## 2. Create `.env` (repo root — gitignored)

```bash
cat > .env <<'EOF'
ANTHROPIC_API_KEY=placeholder
YOUTUBE_API_KEY=placeholder

# Reddit API credentials — REQUIRED (see below). Reddit now blocks the
# unauthenticated public API, so without these you get 0 results.
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
# Optional but recommended for a "script" app — full user (password) grant:
REDDIT_USERNAME=your_reddit_username
REDDIT_PASSWORD=your_reddit_password
EOF
```

`ANTHROPIC_API_KEY` / `YOUTUBE_API_KEY` are required only so `config.py` imports;
the Reddit code never calls them, so **placeholders are fine** for those two.

### Getting the Reddit credentials (required)

Reddit 403-blocks the unauthenticated JSON API for essentially all IPs now, so
authenticated access is the only reliable path:

1. Go to <https://www.reddit.com/prefs/apps> and **create another app…**.
2. Choose type **script**.
3. Set redirect uri to `http://localhost:8080` (unused, but required).
4. After creating, copy:
   - the **client id** (the string just under the app name) → `REDDIT_CLIENT_ID`
   - the **secret** → `REDDIT_CLIENT_SECRET`
5. `REDDIT_USERNAME` / `REDDIT_PASSWORD` are the Reddit account that owns the app.
   With them, the client uses the full user (password) grant; without them it
   uses read-only app-only OAuth (also fine for searching).

`client_id` + `client_secret` alone is enough to start; add username/password if
read-only mode is rejected. Authenticated OAuth talks to `oauth.reddit.com`,
which is **not** IP-blocked — so it works locally *and* from GitHub Actions.

## 3. Smoke test — confirm live Reddit access

```bash
python -m casino_dashboard.jobs.reddit_smoke_test RKLB ASTS
```

Expect a table with **non-zero** post counts. If everything is `0` with
`403 Blocked` in the logs, your IP is blocked too — stop and see
[Optional: cloud / authenticated](#optional-cloud--authenticated).

## 4. Discover subreddits and save the map

```bash
# Prints a ranked report AND writes config/ticker_subreddits.yaml
python -m casino_dashboard.jobs.subreddit_discovery_run RKLB ASTS "Rocket Lab" IONQ OKLO --save
```

- Each query is a **ticker or a company name** (names resolve to a ticker first).
- Ranks candidate subreddits by subscribers, currently-online, measured
  posts/7d, and name/description relevance; drops noise; flags tickers where
  nothing solid was found.
- `--save` writes the **selected** subreddits per ticker to
  `config/ticker_subreddits.yaml`.

Review and commit the map (it's a small config file — safe to commit, unlike the DB):

```bash
cat config/ticker_subreddits.yaml     # eyeball matches; hand-edit freely
git add config/ticker_subreddits.yaml
git commit -m "Update discovered subreddit map"
```

Re-running discovery for a ticker overwrites only that ticker; other entries
(including manual edits) are preserved.

### 4b. Catalog sweep — the top-down alternative

Discovery above is **bottom-up**: it guesses names for one ticker at a time
(r/RKLB, r/RKLBstock, r/RocketLab, …) and probes each guess, so it can only find
communities somebody thought to name. The catalog sweep goes the other way —
enumerate the subreddits that exist, sorted by subscriber count, then filter:

```bash
# Stage 1 all subs -> stage 2 stock subs -> stage 3 per-stock subs
python -m casino_dashboard.jobs.subreddit_catalog_run

# Go deeper (smaller communities), dump the full catalog for offline work
python -m casino_dashboard.jobs.subreddit_catalog_run \
    --min-subscribers 250 --max-requests 1500 \
    --out research/probes/subreddit_catalog

# Re-filter that saved sweep offline — no network, no waiting — and save the map
python -m casino_dashboard.jobs.subreddit_catalog_run \
    --from-catalog research/probes/subreddit_catalog/<date>/catalog.csv --save
```

Sweep once, filter many times: `--from-catalog` replays a saved `catalog.csv`
through stages 2–3, so tuning thresholds or writing the map costs nothing.

- **Stage 1** asks Arctic Shift for subreddits **ranked by subscriber count**
  (`sort_type=subscribers`, 1000 per page) and walks down to
  `--min-subscribers`. If that query shape is rejected the sweep degrades —
  creation-time paging, then a name-prefix walk — and the report names the shape
  that ran, so a partial sweep is never passed off as a census. Either way it
  flags itself when `--max-requests` runs out.
- **Stage 2** keeps the stock / stock-market subs, judged on whole-token matches
  in the name (r/StockMarket, r/pennystocks) or unmistakably financial
  title/description text. Token matching is what keeps r/Stockholm, r/marketing
  and r/livestock out.
- **Stage 3** attributes a sub to one ticker using the same relevance scorer as
  bottom-up discovery, gated on `--ticker-min-subscribers`. A sub that matches
  two stocks equally is left unattributed rather than guessed.

Cost scales with how far the floor drops — about one request per 1,000
subreddits above it on the ranked walk, ten times that on the creation-time
fallback. Start at the default 1,000. Also runnable from Actions — **Subreddit
Catalog (live, read-only)** — which uploads `catalog.csv` + `per_stock.json` as
artifacts.

**Below the floor, use the per-ticker pass.** A ranked sweep cannot see under
`--min-subscribers`, and real ticker communities live down there (r/SNDK_Stock
had 22 members, r/CCJ 183). `--with-per-ticker` runs bottom-up `discover()` for
exactly the stocks the sweep found nothing for, so the two passes cover each
other's blind spots:

```bash
python -m casino_dashboard.jobs.subreddit_catalog_run --with-per-ticker --save
```

**`--newest-first` only matters on the creation-time fallback.** That shape walks
by date, so a truncated oldest-first run covers 2005 onward and stops — the wrong
end of history, since ticker subs are recent. The ranked walk is ordered by size,
so the flag does nothing there.

## 5. Pull Reddit posts into the DB

```bash
# Specific tickers:
python -m casino_dashboard.jobs.reddit_refresh RKLB ASTS IONQ OKLO

# ...or the whole universe:
python -m casino_dashboard.jobs.reddit_refresh
```

Uses each ticker's mapped subreddits (falls back to the default finance subs for
unmapped tickers) and writes to `data/snapshots.db`.

Tuning:

```bash
REDDIT_POSTS_PER_TICKER=50 python -m casino_dashboard.jobs.reddit_refresh RKLB
```

## 6. Verify what landed

```bash
sqlite3 data/snapshots.db "SELECT COUNT(*) AS posts FROM reddit_posts;"
sqlite3 data/snapshots.db "SELECT ticker, subreddit, score, substr(title,1,50) \
  FROM reddit_posts ORDER BY score DESC LIMIT 15;"
```

## ⚠️ Committing the database

`data/snapshots.db` is **production data**, normally committed only by the daily
GitHub Action. A local run can overwrite good production rows with a partial
result. Prefer committing only `config/ticker_subreddits.yaml`. If you must
commit the DB, `git pull` first, run a full refresh, verify it's a superset, and
avoid pushing while a scheduled refresh (2am/9am/1pm/5pm ET) is running.

## Optional: cloud / authenticated

Set any of these in `.env` (local) or as repo Secrets/Variables (Actions):

| Variable | Purpose | Where to get it |
|----------|---------|-----------------|
| `REDDIT_BACKEND` | Force a backend: `arctic_shift` (free default), `apify`, or `direct`. | n/a |
| `APIFY_TOKEN` | Enables the Apify managed scraper (intraday-fresh full posts). When set, the pull uses Apify. | apify.com → Settings → Integrations → API token |
| `APIFY_REDDIT_ACTOR` | Which Apify actor to run (default `trudax~reddit-scraper`). | Apify Store (`username~actor-name`) |
| `APIFY_REDDIT_INPUT` | Optional JSON to override the actor input; use `{query}` for the ticker. | your chosen actor's input schema |
| `APEWISDOM_SUBREDDITS` | Comma-separated subreddit filters for the per-subreddit breakdown (default WSB/stocks/investing/options/stockmarket). | n/a |
| `REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET` / `REDDIT_USERNAME` / `REDDIT_PASSWORD` | Authenticated PRAW (`REDDIT_BACKEND=direct`). Requires a Reddit app, whose creation is currently gated. | `reddit.com/prefs/apps` → "script" app |

> **Note:** the credential-less direct scraping path (public JSON + browser
> impersonation + proxy) was removed — Reddit killed that endpoint, so it could
> never work. Access now goes through Arctic Shift (free) or Apify (paid).

When `REDDIT_CLIENT_ID`/`SECRET` are set, the scraper auto-upgrades to
authenticated PRAW; otherwise it uses the public JSON API.

## Command reference

| Command | What it does | Writes |
|---------|--------------|--------|
| `python -m casino_dashboard.jobs.reddit_smoke_test [TICKERS…]` | Live probe; prints post counts | nothing |
| `python -m casino_dashboard.jobs.subreddit_discovery_run [QUERIES…] [--save]` | Discover + rank subreddits; `--save` writes the map | `config/ticker_subreddits.yaml` (with `--save`) |
| `python -m casino_dashboard.jobs.subreddit_catalog_run [--save] [--out DIR] [--from-catalog CSV]` | Sweep all subreddits by subscribers → stock subs → per-stock subs (`--from-catalog` re-filters a saved sweep offline) | `config/ticker_subreddits.yaml` (with `--save`), `DIR/` (with `--out`) |
| `python -m casino_dashboard.jobs.reddit_refresh [TICKERS…]` | Pull posts into the DB (Reddit only) | `data/snapshots.db` |
