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

**Start with the resolver.** It is the front door to the map, with two inputs:

```bash
# A company name (or ticker): shows ranked candidates; saves nothing on its own
python -m casino_dashboard.jobs.subreddit_resolve company "Rocket Lab"
python -m casino_dashboard.jobs.subreddit_resolve company "Rocket Lab" --save          # the confident ones
python -m casino_dashboard.jobs.subreddit_resolve company "Rocket Lab" --pick RocketLab # exactly these

# A subreddit you already know: filed under the stock it's about, else general
python -m casino_dashboard.jobs.subreddit_resolve add RocketLab                # → RKLB
python -m casino_dashboard.jobs.subreddit_resolve add wallstreetbets           # → general list
python -m casino_dashboard.jobs.subreddit_resolve add r/SomeSub --ticker RKLB  # you decide, no lookup
python -m casino_dashboard.jobs.subreddit_resolve add r/SomeSub --general      # you decide, no lookup

python -m casino_dashboard.jobs.subreddit_resolve list
python -m casino_dashboard.jobs.subreddit_resolve remove r/RKLB --ticker RKLB
```

The **Subreddits** page in the dashboard does the same with two input fields.
The company search uses the same prefix matcher as `subreddit_match_run`;
adding by name uses the catalog sweep's attribution rule (name form, or a
description naming the ticker/company in a finance context; a tie between two
stocks counts as no match). The
sections that follow are the older bulk tools, still useful for sweeping the
whole universe; their `--save` keeps any subreddit you added by hand.

### 4a. Discovery runner

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
enumerate the subreddits that exist, sorted by subscriber count, then filter.

Run it in **two phases** — fetch, then filter. Fetching is the slow half
(rate-limited, minutes long, easy to lose); filtering is the half worth redoing
whenever a threshold looks wrong.

```bash
# PHASE 1 — dump every subreddit + subscriber count. No filtering, no yfinance.
python -m casino_dashboard.jobs.subreddit_catalog_run --fetch-only \
    --min-subscribers 100 --out research/probes/subreddit_catalog

# PHASE 2 — filter that file into stock subs -> per-stock subs. No network.
CSV=research/probes/subreddit_catalog/$(date +%F)/catalog.csv
python -m casino_dashboard.jobs.subreddit_catalog_run --from-catalog $CSV
python -m casino_dashboard.jobs.subreddit_catalog_run --from-catalog $CSV --save
```

Phase 1 streams rows to the CSV as they arrive, so a walk that times out or gets
cancelled still leaves everything it had already seen. Phase 2 costs nothing and
can be re-run as often as the thresholds need.

One command still does both (`subreddit_catalog_run` with no `--fetch-only`);
the split just stops a threshold tweak from re-paying for the fetch.

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

**Set the floor low for per-stock subs.** Real single-stock investor communities
are small — r/MPMaterials (392), r/Lunr (674), r/Ciena (316), r/MU_Stock (404),
r/CAPR_Stock (123) — so the default 1,000 floor drops nearly all of them. Use
`--min-subscribers 100` when the goal is the per-stock map, and the default only
when you want the big market subs. Cost scales with how far the floor drops:
about one request per 1,000 subreddits above it on the ranked walk, ten times
that on the creation-time fallback. Also runnable from Actions — **Subreddit
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
so the flag does nothing there; if a ranked run reports "Incomplete sweep", the
remedy is a bigger `--max-requests` (or a higher floor), not a direction change.
`--max-requests` counts pages in every strategy, but a ranked page is 1,000
subreddits against the creation-time walk's 100.

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

## 5b. Scrape a subreddit, or search Reddit by keyword

`reddit_scrape` reads posts on demand. It uses Arctic Shift, needs no keys, and
works from a laptop or from the **Reddit Scrape** workflow in the Actions tab.

**Read whole subreddits:** every post in the window, with no text filter. Use
this for a stock's own community, where a post like "BlueBird launch news" is
about the stock even though it never says "ASTS".

```bash
python -m casino_dashboard.jobs.reddit_scrape subreddit ASTSpaceMobile RKLB
python -m casino_dashboard.jobs.reddit_scrape subreddit wallstreetbets --days 1 --sort comments
```

**Search by keyword:** posts that mention any of the keywords. It searches all
of Reddit, or only the subreddits you name with `--subreddits`. Each result is
re-checked as a whole word: an all-capitals keyword like `PATH` has to appear
in capitals (`PATH` or `$PATH`), so "career path" and "Paired-Path" don't count.
Other keywords, like `rocket lab`, match in any case.

```bash
python -m casino_dashboard.jobs.reddit_scrape search "rocket lab" RKLB Neutron
python -m casino_dashboard.jobs.reddit_scrape search '$ASTS' --subreddits wallstreetbets,stocks
```

If the archive refuses a Reddit-wide search, the report says so and searches
wallstreetbets, stocks, investing, options and StockMarket instead.

Options for both modes:

| Option | Default | Meaning |
|---|---|---|
| `--days N` | 7 | How far back to look |
| `--limit N` | 25 | Posts returned after ranking |
| `--sort` | `top` | `top` (score), `new` (date) or `comments` (comment count) |
| `--comments N` | 0 | Also pull each post's top N comments. This is where a daily discussion thread's content is. |
| `--json PATH` | — | Save the full result (whole post bodies and comments) as JSON |
| `--save --ticker T` | — | Store the posts in `data/snapshots.db` under ticker T. Don't commit that file (see below). |

The command prints a table (score, comments, age, subreddit, title) and then
each post's opening text and top comments. For example:

```
## Reddit scrape — r/ASTSpaceMobile
Last 7d · sorted by top · 25 posts
| # | Score | Comments | Age | Subreddit | Title |
| 1 | 112 | 521 | 2d | r/ASTSpaceMobile | AST SpaceMobile - $ASTS - Daily Discussion Thread |
…
```

## 5c. Daily ingestion into `reddit.db`

The scheduled way to collect Reddit: **`reddit_ingest.yml`** runs daily. For every
stock it reads the subreddits in the map, searches the general list for the
ticker and company name, saves the top comments on busy posts, and commits
`data/reddit.db`. Design and limits: [reddit-ingestion-v1](../specs/reddit-ingestion-v1.md).

Run it by hand against a scratch file (never commit a local `reddit.db`):

```bash
REDDIT_DB_PATH=/tmp/reddit.db python -m casino_dashboard.jobs.reddit_ingest RKLB ASTS
```

It prints a report: posts new vs re-seen, comments saved, rows pruned, file
size, a per-stock table, and a "Problems" list (e.g. `archive unreachable`).
A run that stored nothing exits with code 1.

## 5d. The daily digest (LLM brief per stock)

Right after ingestion, the same workflow writes each stock's digest — a short
brief and linked insights shown on Ticker Detail. Design:
[reddit-digest-v1](../specs/reddit-digest-v1.md).

Which model writes it is set by `REDDIT_DIGEST_LLM`:

| Value | Model | Needs |
|---|---|---|
| `auto` (default) | Claude if the Claude Code CLI is installed, else Gemini | — |
| `claude` | Claude Code CLI (`claude -p`) on a Claude subscription. Counts against the plan's usage limits, never API billing. Model: `REDDIT_DIGEST_CLAUDE_MODEL` (default `haiku`) | Locally: `claude` installed and signed in. In Actions: secret `CLAUDE_CODE_OAUTH_TOKEN` (from `claude setup-token`); the workflow installs the CLI only when it's set |
| `gemini` | Gemini free tier. Model: `REDDIT_DIGEST_MODEL` (default `gemini-flash-lite-latest`) | `GEMINI_API_KEY` |

The Claude client removes `ANTHROPIC_API_KEY` from the CLI's environment, so a
key in `.env` or the workflow can never switch it to API billing. It also runs
the CLI with no tools (`--tools ""`): Reddit text is untrusted, and the model
can only answer.

```bash
# On your own computer, with Claude Code signed in:
REDDIT_DB_PATH=/tmp/reddit.db REDDIT_DIGEST_LLM=claude \
  python -m casino_dashboard.jobs.reddit_digest RKLB ASTS

# Or on Gemini:
GEMINI_API_KEY=... REDDIT_DB_PATH=/tmp/reddit.db REDDIT_DIGEST_LLM=gemini \
  python -m casino_dashboard.jobs.reddit_digest RKLB ASTS
```

On Claude, each stock with new posts takes about 30–60 seconds.

Run it after an ingest into the same scratch file. Expect
`## Reddit digest — ✅ ok`, an insight count per stock, and "Quiet" for stocks
with no new posts. Look at the result:

```bash
sqlite3 /tmp/reddit.db "SELECT ticker, status, mood, summary FROM digests;"
sqlite3 /tmp/reddit.db "SELECT ticker, kind, stance, headline FROM insights;"
```

"⚠️ Stopped early: …" gives the reason and lists the stocks not digested
(the next run covers them). The usual reasons:

| Reason in the report | Meaning | Fix |
|---|---|---|
| `daily free-tier quota used up` | Google's daily allowance is spent | Wait a day. If `REDDIT_DIGEST_MODEL` is set to a full Flash model, clear it: Flash's free tier is ~20 requests/day |
| `HTTP 400 … API key not valid` | The secret is wrong | Re-copy the key from AI Studio |
| `HTTP 402 … prepayment credits are depleted` | The key belongs to a *billed* project with no credit | Use a key from a project without billing (free tier), or top it up |
| `HTTP 404 … no longer available` | The pinned model was retired | Clear `REDDIT_DIGEST_MODEL`, or set a current model |
| `Claude plan usage limit reached` | The Claude plan's 5-hour or weekly allowance is spent (shared with your own Claude use) | Wait for it to reset; the next run covers the skipped stocks |
| `Claude CLI isn't signed in to a subscription` | `CLAUDE_CODE_OAUTH_TOKEN` is wrong or expired (locally: not signed in) | Run `claude setup-token` again and replace the secret (locally: run `claude` and sign in) |
| `Claude CLI exited …` | The CLI crashed or didn't install | Check the "Install Claude Code CLI" step's log |

## 5e. The digest on your own computer (Claude subscription, scheduled)

`scripts/reddit_brief_local.sh` (via `./run reddit-brief …`) writes the digest
locally, on the owner's computer, with the Claude Code login already there, so there's no
token in GitHub and no API key. GitHub Actions keeps doing the daily ingest;
the on-demand command also fetches from Reddit itself (Arctic Shift, reachable
from a home connection) for the stocks you name. It publishes only the digest
rows — the posts it fetched stay in a scratch file (`on-demand.db`), and each
insight carries copies of its source posts, so the links on the page work.

| Command | Does |
|---|---|
| `./run reddit-brief RKLB [ASTS…] [--days N]` | **On demand.** Fetches exactly the last N days (default 7) of Reddit posts for those stocks on this computer (`reddit_ingest --days`), has Claude analyse **all** of them (`reddit_digest --days --show`, not only unread posts), prints the insights, and publishes the digest rows like the scheduled run. First use runs `check` |
| `./run reddit-brief check` | Checks the prerequisites, prompting until each is fixed: macOS/Linux, git, uv (offers to install it) or Python 3.11+, `claude`, a working subscription login (one tiny `claude -p` call with API-key variables removed), `main` having the Claude digest code, and push access (`git push --dry-run`) |
| `./run reddit-brief install` | `check`, then sets up a private clone, its Python packages, and the schedule: **launchd** agent on macOS (at log-in + hourly), **systemd user timer** on Linux (3 min after log-in + hourly), else **cron** (`@reboot` + hourly). Offers a first run |
| `./run reddit-brief run [--force]` | What the scheduler runs (see below). `--force` digests even if the latest collection was already done |
| `./run reddit-brief status` | Scheduled? Last collection digested, and the tail of the latest log |
| `./run reddit-brief uninstall` | Removes the schedule (keeps any other cron lines); offers to delete its folder |

Everything lives in `~/.local/share/ticker-reddit-brief/` (`TICKER_BRIEF_HOME`
to move it): `repo/` (a private clone, never your working copy — so hourly
resets and pushes can't touch your own branch or uncommitted work), `logs/`
(one file per UTC day, kept 30 days), `config` (clone URL, branch, and the PATH
captured at install, since schedulers start jobs with a bare PATH), and
`bin/reddit-brief.sh` (a copy of the script, so updating the clone can't change
it mid-run; re-run `install` to pick up a newer script).

The clone is deliberately tiny (~3 MB): the repository commits two ~30 MB
databases several times a day, so a full clone is several GB. It is shallow
(`--depth 1`), blobless (`--filter=blob:none`, contents fetched on demand) and
sparse (no `research/`, and of `data/` only `reddit.db`), and is compacted after
each run.

**Each hourly run:**

1. Fetches the latest `main` (a few KB) and compares the object id of
   `data/reddit.db` with the one it saw last time. Unchanged → nothing to do,
   nothing downloaded. No `data/reddit.db` on `main` → nothing to do. Otherwise
   resets the private clone to `origin/main`.
2. Reads the newest finished ingest in `runs`. Same as the last one digested →
   nothing to do, **no Claude call**. So it digests once per GitHub collection
   (daily), and catches up the next time the computer is on.
3. Runs the digest (`REDDIT_DIGEST_LLM=claude`) on a scratch copy.
4. Publishes: fetches `main` again, merges **only the digest rows** into the
   newest `data/reddit.db` (`reddit_digest_merge`: newer replaces older, never a
   good digest with a quiet/failed one), commits as `reddit-brief-local`,
   pushes. A rejected push (main moved) → merge again, up to 4 tries.
5. Records the ingest it digested — unless the run stopped early (e.g. the
   plan's usage limit), in which case the next hourly check retries.

This is the one sanctioned writer of `data/reddit.db` outside GitHub Actions: it
never pushes back a whole local copy, only new digest rows on top of `main`.

Troubleshooting: `./run reddit-brief status`, then the log it names. A push
that keeps failing usually means git's GitHub login expired: run
`gh auth login` (or fix your SSH key) and `./run reddit-brief check`.

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
| `python -m casino_dashboard.jobs.subreddit_catalog_run --fetch-only --out DIR` | Phase 1: dump every subreddit + subscriber count | `DIR/` |
| `python -m casino_dashboard.jobs.subreddit_catalog_run --from-catalog CSV [--save]` | Phase 2: filter that dump → stock subs → per-stock subs (no network) | `config/ticker_subreddits.yaml` (with `--save`), `DIR/` (with `--out`) |
| `python -m casino_dashboard.jobs.subreddit_resolve company "NAME" [--save \| --pick A,B]` | Find a company's subreddits; save the confident ones or your picks | `config/ticker_subreddits.yaml` (with `--save`/`--pick`) |
| `python -m casino_dashboard.jobs.subreddit_resolve add NAME [--ticker T \| --general]` | Add a subreddit: filed under the stock its name/description match, else the general list; `--ticker`/`--general` decide it yourself | `config/ticker_subreddits.yaml` |
| `python -m casino_dashboard.jobs.reddit_digest [TICKERS…]` | Daily LLM brief + linked insights per stock (Claude Code CLI on a subscription, or `GEMINI_API_KEY`) | `digests`, `insights` in `data/reddit.db` |
| `python -m casino_dashboard.jobs.reddit_ingest [TICKERS…]` | Daily ingestion: posts + top comments per stock | `data/reddit.db` (or `REDDIT_DB_PATH`) |
| `python -m casino_dashboard.jobs.reddit_refresh [TICKERS…]` | Pull posts into the DB (Reddit only) | `data/snapshots.db` |
| `python -m casino_dashboard.jobs.reddit_scrape subreddit SUBS… [--comments N]` | Every post in whole subreddits, ranked | nothing (`--json PATH`, `--save --ticker T` optional) |
| `python -m casino_dashboard.jobs.reddit_scrape search KEYWORDS… [--subreddits A,B]` | Keyword search, whole-word matched, ranked | nothing (`--json PATH`, `--save --ticker T` optional) |
