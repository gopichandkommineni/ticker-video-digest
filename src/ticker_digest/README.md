# `ticker_digest/` — the YouTube insight thread

The project's **original** idea, and the reason the repository is called
`ticker-video-digest`: watch what stock commentators say on YouTube, and
summarise it with AI so you don't have to sit through hours of video.

It now runs end to end. Point it at a ticker (or at a channel you already
trust), and it comes back with a **thread**: a short, ordered list of posts
about what was said, with every claim marked as new, developing or already
known, and every claim clickable back to the second of video it came from.

```bash
python -m ticker_digest ticker RKLB                       # search YouTube
python -m ticker_digest ticker RKLB --channel @spaceinvesting   # one channel
python -m ticker_digest threads --ticker RKLB             # what you saved earlier
python -m ticker_digest threads --show 4f2a91c0d3b7       # print one in full
```

You need `YOUTUBE_API_KEY` and `ANTHROPIC_API_KEY` in `.env`.

---

## Why "new" is the whole point

Most YouTube commentary about a stock repeats the same bull case week after
week. A digest that just summarises the videos would tell you the same thing
every time you ran it.

So every claim is stored, and every run is judged against what's already
stored. What you read is the *delta*:

| Verdict | Means |
|---|---|
| `new` | Nothing on record covered this before |
| `developing` | An update to something tracked — a firmer date, a revised number |
| `known` | A restatement of something already on record |

The first run for a ticker has nothing to compare against, so everything is
`new`. The second run is where it starts earning its keep.

There's a fourth case that isn't a verdict: a `known` claim repeated by a
channel that had never said it before. The claim is old; the agreement is what
changed. Those are flagged `newly_corroborated` and rank above plain `known`.
Channels, not videos — one commentator posting three times is one source.

---

## What's here

| File | Does |
|---|---|
| `quality.py` | Which videos are worth reading, and how much to trust each one. Pure functions, no network. |
| `youtube_client.py` | Finds videos — by search, or from one channel |
| `transcripts.py` | Pulls the captions out of a video (cached 30 days) |
| `analyzer.py` | Per-video extraction: catalysts, red flags, events, sentiment |
| `novelty.py` | Is any of this actually new? Also ranks what the thread sees. |
| `thread.py` | Writes the thread |
| `store.py` | SQLite: runs, claims, threads |
| `pipeline.py` | Wires the above together |
| `cli.py` | The command-line entry point |

## The flow

```
   ticker  ──► YouTube search ──┐
                                ├──► quality filter ──► reliability ranking
   channel ──► channel uploads ─┘                              │
                                                               ▼
                          transcripts (cached) ──► per-video extraction (Sonnet)
                                                               │
                                                               ▼
                    claims  ──►  novelty check  ──►  thread (Opus)  ──►  SQLite
                                      ▲                                    │
                                      └──── claims from earlier runs ◄──────┘
```

Two models, on purpose: a cheaper one per video (that cost grows with the
number of videos), a stronger one once at the end.

## Picking sources

**Ticker input.** YouTube search returns whatever it returns, so the results go
through a filter and then a ranking:

- *dropped* — under 120 seconds, channels under 500 subscribers, or a title
  that's shouted or stuffed with 🚀🔥 emoji
- *ranked* — subscribers (30%), views (25%), views-per-subscriber (15%),
  duration (15%), recency (15%)

Views-per-subscriber is in there deliberately: a 2k-subscriber channel with a
30k-view video said something people passed around. Every weighting lives in
`core/config.py`; the scoring itself is in `quality.py` and is unit-tested
without an API key.

**Channel input.** When you already trust a commentator, `--channel` takes a
name, an `@handle`, a channel URL or a raw channel id. Their uploads are
narrowed to the ticker first, so a digest about RKLB doesn't ingest their
Bitcoin video. If the name matches nothing, the run stops and says so rather
than quietly falling back to a search.

## Novelty, in two stages

Cheap first. Each claim is normalised to a token set and compared against
stored claims: an exact fingerprint match, or a Jaccard similarity over the
threshold, is a restatement — marked `known` for free.

Only what survives goes to the model, *with* the known claims as context, which
is what catches a paraphrase the token overlap missed. On a first run, or when
nothing survives, no model call happens at all.

What reaches the thread arrives pre-ranked by `rank_claims`: new, then
developing, then newly corroborated, then known — and within a band, whatever
more sources said. The model decides what deserves a post; it doesn't decide
what leads.

## Where it stores things

`data/digests.db` — its own database, not the dashboard's `snapshots.db`.
Git-ignored: this is your reading history, not production data. Override the
location with `TICKER_DIGEST_DB`.

Four tables: `digest_runs` (the whole run), `claims` (identity — one row per
distinct claim per ticker, where `first_seen_at` is never overwritten and *is*
the novelty check), `claim_citations` (evidence — one row per video that made
the claim, with the channel that published it), and `threads`.

An older database migrates itself on first open; there's no script to run.
Citations recovered from a pre-split database are marked with an unknown
channel, and corroboration stays unflagged for those rather than guessed.

## Also here: the Market Reality Check

```bash
python -m ticker_digest market --thesis
```

Prints the same Reality Score the dashboard shows, in the terminal. The logic
behind it lives in [`core/market/`](../core/README.md), not here — this package
just exposes it as a command.

## Tests

`tests/test_digest_*.py`, plus `test_youtube_client.py`,
`test_youtube_channels.py`, `test_transcripts.py` and `test_analyzer.py`.
Nothing hits the network or an LLM.

## Caveats

- YouTube search quota is 100 units per query — a run is a handful of calls,
  but a loop over 64 tickers is not free.
- Captions are unavailable on plenty of videos. Those are skipped, with the
  reason reported; the run continues.
- The output is aggregated commentary from strangers on the internet. Every
  thread carries the disclaimer for a reason.
