# Reddit data — local runbook

How to pull Reddit data: discover which subreddits belong to each stock, save
that map, and pull posts + mention signal into the database.

> **⚠️ Reddit closed the direct paths (2026).** Reddit shut down its public JSON
> API and put remaining access behind Cloudflare, so direct fetches — even
> browser-impersonated, even via residential proxy — are unreliable, and new API
> app creation is gated. The code therefore supports two **managed** data
> sources that handle this for you:
>
> - **Apify** (full post content) — a managed scraper that solves Cloudflare.
>   Set `APIFY_TOKEN` and the Reddit pull uses it automatically. Small cost.
> - **ApeWisdom** (aggregated mention signal) — free, no credentials, already
>   wired into the daily refresh, incl. a per-subreddit breakdown.
>
> The direct client (public JSON / PRAW / proxy) still exists as a fallback but
> is no longer reliable on its own.

## 0. Choose a backend

- **Full posts** → get an [Apify](https://apify.com) account + API token, set
  `APIFY_TOKEN`. The pull auto-selects Apify when the token is present.
- **Just mention signal / free** → set nothing; ApeWisdom runs in the daily
  refresh and gives per-ticker and per-subreddit mention counts + velocity.

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
| `APIFY_TOKEN` | Enables the Apify managed scraper (full post content, solves Cloudflare). When set, the pull uses Apify. | apify.com → Settings → Integrations → API token |
| `APIFY_REDDIT_ACTOR` | Which Apify actor to run (default `trudax~reddit-scraper`). | Apify Store (`username~actor-name`) |
| `APIFY_REDDIT_INPUT` | Optional JSON to override the actor input; use `{query}` for the ticker. | your chosen actor's input schema |
| `APEWISDOM_SUBREDDITS` | Comma-separated subreddit filters for the per-subreddit breakdown (default WSB/stocks/investing/options/stockmarket). | n/a |
| `REDDIT_IMPERSONATE` | Browser to impersonate at the TLS layer (default `chrome`). Set to `none` to disable and use plain requests. | n/a — built in via `curl_cffi` |
| `REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET` | Authenticated PRAW — works from cloud IPs | `reddit.com/prefs/apps` → "script" app |
| `REDDIT_PROXY` | Route traffic through an allowed IP (`http://user:pass@host:port`) | A proxy provider |
| `REDDIT_USER_AGENT` | Override the request User-Agent | A descriptive string, e.g. `casino-dashboard/0.1 by u/you` |

> **Browser impersonation is on by default.** Reddit blocks requests that don't
> look like a real browser (by TLS fingerprint, not just User-Agent), so the
> client uses `curl_cffi` to impersonate Chrome. This is what makes the
> credential-less public path work. If it's ever *still* blocked, the next step
> is a real headless browser (Playwright) — not yet wired in.

When `REDDIT_CLIENT_ID`/`SECRET` are set, the scraper auto-upgrades to
authenticated PRAW; otherwise it uses the public JSON API.

## Command reference

| Command | What it does | Writes |
|---------|--------------|--------|
| `python -m casino_dashboard.jobs.reddit_smoke_test [TICKERS…]` | Live probe; prints post counts | nothing |
| `python -m casino_dashboard.jobs.subreddit_discovery_run [QUERIES…] [--save]` | Discover + rank subreddits; `--save` writes the map | `config/ticker_subreddits.yaml` (with `--save`) |
| `python -m casino_dashboard.jobs.reddit_refresh [TICKERS…]` | Pull posts into the DB (Reddit only) | `data/snapshots.db` |
