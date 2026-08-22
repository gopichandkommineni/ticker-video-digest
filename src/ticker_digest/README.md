# `ticker_digest/` — the YouTube digest (placeholder)

The project's **original** idea, and the reason the repository is called
`ticker-video-digest`: watch what stock commentators say on YouTube, and
summarise it with AI so you don't have to sit through hours of video.

**It is not finished.** The modules exist and much of the machinery works, but
the feature isn't wired up end to end. It's on the roadmap, not in production.

Don't delete it — it's deliberately kept.

---

## What's here

| File | Does | State |
|---|---|---|
| `youtube_client.py` | Finds videos via the YouTube Data API | Written |
| `transcripts.py` | Pulls the captions out of a video | Written |
| `analyzer.py` | The two-pass AI summarisation | Written |
| `cli.py` | The command-line entry point | Written |
| `__main__.py` | Makes `python -m ticker_digest` work | Written |

## The one part that *is* live

The CLI has two subcommands, and one of them is used daily:

```bash
python -m ticker_digest ticker RKLB      # the YouTube digest — placeholder
python -m ticker_digest market --thesis  # the Market Reality Check — LIVE ✅
```

`market` prints the same Reality Score the dashboard shows, in the terminal.
The logic behind it lives in [`core/market/`](../core/README.md), not here —
this package just exposes it as a command.

## The intended design

A two-pass AI pipeline, so cost stays predictable as the video count grows:

**Pass 1 — per video.** Transcript in, structured summary out: catalysts, red
flags, upcoming events, sentiment. Every item carries a timestamp so a claim
can be traced back to the second of video it came from.

**Pass 2 — across videos.** All those summaries in, one digest out. Themes
several commentators agree on rank higher; citations are preserved.

Prompt caching is enabled on the system prompt and schema, since they're
identical on every video in pass 1.

## Quality filters (planned, from `CLAUDE.md`)

Before spending money transcribing a video, skip it if:

- it's shorter than 120 seconds
- the channel has fewer than 500 subscribers
- the title is ALL CAPS, or full of 🚀/🔥 emoji

Prefer videos from the last 7 days, sorted by view count.

## To pick this up

1. Read [`analyzer.py`](analyzer.py) — the two-pass design is already expressed
   there in code.
2. Data shapes (`Transcript`, `VideoInsights`, `DigestReport`) are in
   [`core/models.py`](../core/models.py).
3. You'll need `YOUTUBE_API_KEY` and `ANTHROPIC_API_KEY` in `.env`.
4. Tests already exist: `tests/test_youtube_client.py`,
   `tests/test_transcripts.py`, `tests/test_analyzer.py`.
