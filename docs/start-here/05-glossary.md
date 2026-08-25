# 5. Glossary

Every bit of jargon you'll meet in this repository, in plain English. Skim it
once; come back when a word ambushes you.

Two halves: **stock-market words** first, **technical words** second.

---

## Stock-market words

**Ticker** — a stock's short code. `RKLB` is Rocket Lab. The project uses
"ticker" and "stock" interchangeably.

**Universe** — the full list of stocks being watched. Defined in
`config/themes.yaml`. Currently 64 stocks across 12 themes. A stock can belong
to more than one theme (Rocket Lab is in both Space and Defense).

**Sector / theme** — a group of stocks that share a story, like "Nuclear". This
project's central idea is that these move together. In the code the word is
usually `sector`; in conversation it's usually "theme". Same thing.

**Speculative** — a flag on a theme meaning "these could go to zero". Quantum
is flagged speculative; AI Infrastructure isn't.

**OHLCV** — Open, High, Low, Close, Volume. The five numbers that describe one
stock's one trading day. The raw material for everything else.

**Volume** — how many shares changed hands. A **volume spike** means unusually
busy trading, which usually means *something happened*.

**Momentum** — the tendency of a stock that's been rising to keep rising. What
the dashboard is built to spot.

**RSI (Relative Strength Index)** — a standard 0–100 gauge of how hard a stock
has run recently. Above ~70 is conventionally "overbought", below ~30
"oversold". Treat it as a temperature reading, not an instruction.

**52-week high / low** — the highest and lowest price of the past year.
"Distance from high" tells you how far a stock has fallen from its peak.

**Catalyst** — an upcoming event that could move the price: an earnings
report, a contract award, an FDA decision, a launch.

**Red flag** — the opposite: a known reason for caution. Both catalysts and red
flags are hand-written by you in `config/manual_notes.yaml`.

**Earnings** — the quarterly results announcement. **BMO** = before market
open, **AMC** = after market close. Prices often jump around these.

**ETF (Exchange-Traded Fund)** — a basket of stocks you can buy as one. The
project uses theme ETFs as a proxy for "is money flowing into this theme?" —
the mapping is in `config/etf_mapping.yaml`.

**Flows** — money moving into or out of something. Rising flows into a nuclear
ETF suggest institutional interest in the whole theme.

**Breadth** — how *many* stocks are participating in a move. A rally where only
five giant companies rise is narrow and fragile; one where hundreds rise is
broad and healthier.

**Sentiment** — how bullish or bearish people feel, as opposed to what the
numbers say.

**Reality Score** — this project's own composite number, on the Market Reality
Check page. It compares stock-market valuation and sentiment against
real-economy data. **Positive = the market is priced richer than the economy
supports. Negative = the market is discounting weakness.** It is a context
gauge, not a timing signal.

**Z-score** — "how many standard deviations from normal is this?" A way of
putting unrelated measures (unemployment %, a valuation ratio, a put/call
count) on one comparable scale so they can be averaged. The Reality Score is
built from z-scores.

**Buffett indicator** — total stock-market value ÷ the size of the economy. A
rough "is the market expensive?" gauge.

**CAPE** — a price-to-earnings ratio smoothed over ten years, so one bad year
doesn't distort it.

**Put/call ratio** — the ratio of bets on prices falling to bets on prices
rising. A crowd-fear gauge.

**Margin debt** — money investors borrowed to buy stocks. Rising margin debt
means a more leveraged, more fragile market.

**Mag-7 concentration** — how much of the market's value sits in the seven
largest tech companies. High concentration means narrow breadth.

**VIX** — the market's expected volatility over the next month; the "fear
index". Shown on the dashboard for context but deliberately kept *out* of the
Reality Score composite.

**Yield curve / 10Y-2Y** — the gap between 10-year and 2-year government bond
interest rates. When it goes negative ("inverted") it has historically preceded
recessions.

**CPI** — the Consumer Price Index; inflation. **Core CPI** excludes food and
energy, which are noisy.

**M2** — a broad measure of how much money exists in the economy.

**Congressional trades** — US politicians must publicly disclose their stock
trades. The Congress page tracks them. Not a signal so much as a curiosity.

**FinTwit** — "financial Twitter": the community of finance accounts on X. The
`src/fintwit/` package archives their posts.

**Cashtag** — a ticker written with a dollar sign, like `$RKLB`. How stocks are
referenced on social media.

**Not investment advice** — the disclaimer on every screen, and it's meant
literally. This tool organises public information. It doesn't recommend
anything.

---

## Technical words

**Python** — the programming language everything here is written in.

**Streamlit** — the library that turns Python scripts into web pages. It's why
`pages/` works the way it does: drop a `.py` file in that folder and it becomes
a page in the sidebar. No HTML or JavaScript involved.

**localhost:8501** — the address of the dashboard while it's running on *your*
machine. `localhost` means "this computer"; `8501` is Streamlit's usual door
number. Nobody else on the internet can reach it.

**SQLite** — a complete database that lives in one ordinary file. Nothing to
install, nothing to start. `data/snapshots.db` is one.

**Table / row / column** — a database table is a spreadsheet tab: columns are
the fields, rows are the records.

**Query** — a request for data from a database. Written in a language called
SQL.

**Idempotent** — running it twice gives the same result as running it once.
The daily job is idempotent, which is why re-running it is always safe.

**Repository (`db/repository.py`)** — the one module allowed to talk to the
database. Everything else asks it. Keeps the SQL in one place.

**Package / module** — a module is one `.py` file; a package is a folder of
them. `src/` holds four packages.

**Import** — one file using code from another. `from core.cache import ...`
means "get `cache` out of the `core` package".

**Virtual environment (`.venv`)** — a private copy of Python and its libraries,
belonging to this project alone, so its libraries can't collide with another
project's. `./run setup` creates it.

**Dependency** — an outside library the project needs. Listed in
`pyproject.toml`.

**`pyproject.toml`** — the project's spec sheet: name, Python version,
dependencies, tool settings.

**`uv`** — a very fast tool for installing Python dependencies. Optional; `./run
setup` uses it if present and falls back to standard tooling if not.

**YAML (`.yaml`)** — a text format designed to be edited by humans. Indentation
means nesting. Used for every file in `config/`.

> ⚠️ YAML cares about spaces. Indent with **spaces, never tabs**, and keep the
> indentation consistent with the lines around it.

**JSON** — a similar text format, but designed for machines. Used for API
responses and saved probe output.

**API** — the doorway one program uses to ask another for data. Yahoo Finance
has an API; that's how prices arrive.

**API key** — a password identifying you to an API. Kept in `.env` locally and
in GitHub Secrets in production. Never in code.

**Environment variable** — a setting passed to a program from outside it,
rather than written inside it. How every key reaches the code.

**`.env`** — a local file of environment variables. Git-ignored. Never commit
it.

**Git** — the version-control system: a full history of every change.
**GitHub** is the website that hosts it.

**Commit** — one saved change, with a message describing it.

**Branch** — a parallel line of work. `main` is the real one.

**Pull request (PR)** — a proposal to merge a branch into `main`, so it can be
reviewed first.

**GitHub Actions** — GitHub's robots. They run automated jobs on a schedule or
on demand. The files in `.github/workflows/` are their instructions.

**Workflow** — one such robot job.

**Cron** — the syntax for "run at this time". `0 13 * * 1-5` means "13:00 UTC,
Monday to Friday". [crontab.guru](https://crontab.guru) decodes them for you.

**UTC** — the world's reference timezone. The crons are in UTC; the comments
next to them translate to US Eastern.

**Concurrency group** — a lock making sure only one robot writes the database
at a time. Here it's called `db-writer`.

**Secret** — an encrypted value stored on GitHub that workflows can read and
humans can't. Where the production API keys live.

**pytest** — the tool that runs the automated checks in `tests/`.

**Test / fixture / mock** — a test is an automated check. A *fixture* is
canned sample data. A *mock* is a stand-in for something real (like a website)
so tests never need the internet.

**Cache** — a saved copy of a slow answer, kept so it doesn't have to be
fetched again. `config/ticker_company_names.yaml` is a cache.

**Rate limit** — an API's cap on how often you may ask. Exceed it and you get
blocked for a while; `src/fintwit/orchestration/rate_limiter.py` exists to stay
under one.

**Backfill** — going back and filling in historical data that was missed.

**Migration** — a one-time script that reshapes an existing database. The ones
in `scripts/` have already been run; they're kept for the record.

**Probe** — a small experiment answering one empirical question. Everything in
`research/` is a probe plus its saved results.

**Placeholder** — code that exists but isn't finished or wired up. Nothing in
`src/` is a placeholder any more; `src/ticker_digest/` was the last one, and it
now runs from the command line (`./run digest RKLB`).

**Canonical** — in this repo, a file that must not be regenerated or
overwritten without an explicit instruction: `config/themes.yaml` and
`STRATEGY.md`.

---

**Next:** [6. Common tasks →](06-common-tasks.md) · or go back to
[the docs index](../README.md)
