# Reddit Ingestion — v1

**Project:** Casino-Coherent Momentum Dashboard / Reddit
**Date drafted:** 2026-09-27
**Status:** Implemented (store, pipeline, daily workflow). Not yet run against
the live archive. LLM analysis and a dashboard panel are v2 — see §8.

---

## 1. Where this sits

The Reddit side is three components:

| # | Component | Code | Status |
|---|---|---|---|
| 1 | **Resolver** — which subreddits belong to which stock | `core/social_media/reddit/resolver/` | Shipped |
| 2 | **Client** — read a subreddit's feed, search by keyword | `core/social_media/reddit/scrape.py` | Shipped |
| 3 | **Ingestion** — collect posts and threads over time, for analysis | `core/social_media/reddit/ingest/` | **This spec** |

Before this, the only Reddit posts stored were a side-stage of the daily
refresh: at most 25 trending tickers, posts that literally contain the ticker,
newest-first, no comments, no history — and nothing read them.

## 2. Decisions (taken with the owner, 2026-09-27)

| Question | Decision | Why |
|---|---|---|
| Where to store | **New `data/reddit.db`, committed to git** | The deployed dashboard (Streamlit Cloud) can only show what is in git. Kept small on purpose (§6). |
| How often | **Own daily workflow**, `reddit_ingest.yml` | The archive lags 1–2 days, so more than daily gains nothing; a Reddit failure stays out of the main refresh. |
| What per stock | **Its mapped subreddits + a ticker/company search** of the general list | Dedicated communities *and* wallstreetbets-style chatter; unmapped stocks still get something. |
| How much of a thread | **Top comments on notable posts** | Daily discussion threads are where the content is, without storing everything. |

## 3. One run

```
tickers (themes.yaml) ──┐
resolver map ───────────┤  for each stock:
general list ───────────┤    1. feed of each mapped subreddit (every post in the window)
company names cache ────┘    2. search: [TICKER, short company name] in the general list
                              → upsert posts, link post↔stock, snapshot changed scores
                           then: top comments for notable posts
                           then: prune, VACUUM
                           → data/reddit.db  (+ run report in the Actions Summary)
```

- **Window.** From the last good run's start minus a 3-day overlap (the archive
  fills in posts and scores late), capped at 14 days. First run: 7 days.
  A *failed* run doesn't move the window, so nothing is skipped after an outage.
- **Search list.** The resolver's general list; while that is empty, the five
  big finance subreddits (`DEFAULT_SEARCH_SUBREDDITS`).
- **Company name.** From `config/ticker_company_names.yaml`, shortened to its
  distinctive words ("Applied Optoelectronics, Inc." → "Applied
  Optoelectronics").
- **Noisy tickers.** For tickers that are everyday words (PATH, ON, AG…) or 1–2
  letters, a search hit is kept only if the post says `$TICKER` or the company
  name. The client already requires whole-word, capitalised matches.
- **Failure isolation.** Each stock is its own transaction; one failing stock
  makes the run `partial`, not `failed`. "Archive unreachable / HTTP" warnings
  count as errors; "no posts this week" does not.

## 4. Schema (`data/reddit.db`)

| Table | Key | Holds |
|---|---|---|
| `runs` | run_id | window start, counts, `ok`/`partial`/`failed`, errors |
| `posts` | post_id | subreddit, author, title, body (≤10k chars), url, created, latest score & comment count, first/last seen, when comments were fetched |
| `post_tickers` | (post_id, ticker) | `via` = `subreddit` or `search`; `matched` = the subreddit or the keywords. A subreddit link outranks a search link. |
| `post_scores` | (post_id, seen_at) | score history — a row only when score or comment count changed |
| `comments` | comment_id | post_id, `parent_id` (`t3_…` top-level, `t1_…` reply), author, body (≤2k chars), score, created |

A post found for several stocks is one `posts` row with several `post_tickers`
rows. Every write is an upsert, so a re-run is safe.

## 5. Comments

- **Notable** = score ≥ 20 or ≥ 15 comments.
- Top **15** comments by score (any depth), with `parent_id` so the thread's
  shape can be rebuilt.
- Fetched once; re-fetched while the post is under 3 days old and the last fetch
  is over 20 hours old (threads still growing). At most 100 posts per run,
  busiest first.
- Fresh posts show score 0 in the archive until it catches up (~36h); the
  overlap window re-reads them, so a post that turns out busy gets its comments
  on a later run.

## 6. Size — why these limits

`reddit.db` is committed daily, and every commit keeps a full copy in git
history, so size matters more than it would for a local database.

| Control | Default |
|---|---|
| Drop everything older than | 90 days |
| Drop quiet posts (score < 5 and < 3 comments) older than | 14 days |
| Post body / comment body cap | 10,000 / 2,000 chars |
| Comments per notable post / notable posts per run | 15 / 100 |
| Score history | only when it changed |

Rough expectation: a few MB to low tens of MB at steady state. **This is an
estimate** — the run report prints the file size every day; revisit these
limits after the first two weeks of real runs. All of them live in
`IngestConfig` (`ingest/pipeline.py`).

## 7. Operating it

- Scheduled: daily 07:00 UTC, in the `db-writer` queue after the refresh and
  FinTwit. Manual: **Actions → Reddit — Daily Ingest → Run workflow**,
  optionally for a few tickers.
- Locally: `python -m casino_dashboard.jobs.reddit_ingest RKLB` — set
  `REDDIT_DB_PATH` to a scratch file; never commit a local `reddit.db`.
- Exit code 1 only when a run stored nothing at all.

## 8. Not in v1

1. **LLM analysis.** Done as the daily digest —
   [reddit-digest-v1](reddit-digest-v1.md). Novelty across days (the YouTube
   treatment) is still open.
2. **A dashboard panel.** "What Reddit is saying" on Ticker Detail, reading
   `reddit.db`.
3. **Retiring the old posts stage** in the daily refresh (`reddit_posts` in
   `snapshots.db`), once this has run cleanly for a week.
4. **A fresher source.** Apify (paid, same-day) behind the same client calls.

## 9. Open until the first live run

- Whether the archive accepts every query shape used (the client falls back
  where it can; the run report lists anything refused).
- Real run time (estimated 10–20 minutes for 64 stocks) and daily growth.
