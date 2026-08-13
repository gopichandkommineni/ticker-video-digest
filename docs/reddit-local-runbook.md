# Reddit data — local runbook

How to pull Reddit data locally: discover which subreddits belong to each stock,
save that map, and pull posts into the database. Run these **from your own
machine** — Reddit blocks unauthenticated requests from cloud/CI IPs (GitHub
Actions, etc.), but a residential IP works with no credentials.

> **Why local?** The public Reddit JSON API returns `403 Blocked` from
> datacenter IPs. From home it works credential-free. Authenticated PRAW
> (`REDDIT_CLIENT_ID`/`SECRET`) or a residential `REDDIT_PROXY` are the only ways
> to make the cloud path work — see [Optional: cloud / authenticated](#optional-cloud--authenticated).

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
EOF
```

`config.py` refuses to import without these two, but the Reddit code never calls
Anthropic or YouTube, so **placeholders are fine** for everything in this runbook.
(Swap in a real `ANTHROPIC_API_KEY` only once an LLM-analysis step exists.)

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
| `REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET` | Authenticated PRAW — works from cloud IPs | `reddit.com/prefs/apps` → "script" app |
| `REDDIT_PROXY` | Route traffic through an allowed IP (`http://user:pass@host:port`) | A proxy provider |
| `REDDIT_USER_AGENT` | Override the request User-Agent | A descriptive string, e.g. `casino-dashboard/0.1 by u/you` |

When `REDDIT_CLIENT_ID`/`SECRET` are set, the scraper auto-upgrades to
authenticated PRAW; otherwise it uses the public JSON API.

## Command reference

| Command | What it does | Writes |
|---------|--------------|--------|
| `python -m casino_dashboard.jobs.reddit_smoke_test [TICKERS…]` | Live probe; prints post counts | nothing |
| `python -m casino_dashboard.jobs.subreddit_discovery_run [QUERIES…] [--save]` | Discover + rank subreddits; `--save` writes the map | `config/ticker_subreddits.yaml` (with `--save`) |
| `python -m casino_dashboard.jobs.reddit_refresh [TICKERS…]` | Pull posts into the DB (Reddit only) | `data/snapshots.db` |
