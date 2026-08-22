# Casino Dashboard

**A personal stock-watching dashboard.** It follows ~64 hand-picked stocks
grouped into 12 "story" themes (nuclear, space, quantum, AI infrastructure…),
refreshes their numbers four times a day, and shows you which themes and which
stocks are heating up.

It is a private tool for one person's own research. **It is not investment
advice**, and it never places trades or touches a brokerage account.

---

## 👋 New here? Read these five pages, in order

They are written for a non-technical reader. About 30 minutes end to end.

| # | Page | What you get out of it |
|---|---|---|
| 1 | [What is this thing?](docs/start-here/01-what-is-this.md) | The idea behind the dashboard, in plain English |
| 2 | [Get it running](docs/start-here/02-get-it-running.md) | Copy-paste steps to open the dashboard on your own laptop |
| 3 | [Tour of the folders](docs/start-here/03-tour-of-the-repo.md) | What every folder is for, and where to look for things |
| 4 | [How the data flows](docs/start-here/04-how-the-data-flows.md) | Where the numbers come from and how they reach the screen |
| 5 | [Glossary](docs/start-here/05-glossary.md) | Every piece of jargon, defined |

Then keep two more bookmarked for when you actually change something:

- [Common tasks](docs/start-here/06-common-tasks.md) — "how do I add a stock?", "how do I add a note?"
- [When things break](docs/start-here/07-when-things-break.md) — the errors you are most likely to hit, and the fix

The full documentation index lives at **[docs/README.md](docs/README.md)**.

About to change something? Read **[CONTRIBUTING.md](CONTRIBUTING.md)** — it's
short, and it explains the size budgets this repo enforces.

---

## The 60-second version

```bash
./run setup       # one-time: install everything
./run dashboard   # open the dashboard in your browser
```

`./run` is a helper script that wraps the fiddly commands. Type `./run` on its
own to see everything it can do.

What you'll see: a grid of theme cards on the home page, and a sidebar with
more pages — sector rankings, a table of every stock, a per-stock detail page,
a broad "is the whole market expensive?" check, congressional trading
disclosures, and a form for adding new stocks.

---

## How it stays up to date

Nobody has to run anything by hand. A scheduled job on GitHub
(`.github/workflows/daily_refresh.yml`) wakes up **four times every weekday** —
2am, 9am, 1pm and 5pm US Eastern — downloads fresh prices and social-media
chatter, recalculates every signal, and saves the results into a single file,
`data/snapshots.db`. That file is committed straight back into this repository,
which is why the dashboard is fast: it reads finished numbers rather than
calling the internet while you wait.

> ⚠️ **`data/snapshots.db` is live production data.** Never commit your own
> local copy of it — you would overwrite the real history with test results.
> See [When things break](docs/start-here/07-when-things-break.md#i-accidentally-changed-the-database).

---

## What's in the box

```
app.py            The dashboard's home page (start here if you're reading code)
pages/            The other dashboard pages — one file per page in the sidebar
config/           Hand-edited settings: which stocks, which themes, your notes
data/             The saved results (two SQLite database files)
src/              All the real logic, split into four packages (see below)
scripts/          One-off maintenance commands run by a human
tests/            Automated checks that the logic still works
docs/             Everything written down — start at docs/README.md
research/         Old experiments, kept as a record. Safe to ignore.
.github/workflows/ The scheduled robots that keep the data fresh
```

Every one of those folders has its own `README.md` explaining it in more
detail. Click into any folder on GitHub and you'll get an explanation.

### The four code packages under `src/`

| Package | Plain English | Status |
|---|---|---|
| `casino_dashboard` | **The product.** The dashboard, its data fetching, its database, its signals, its screens. | Live |
| `core` | Shared plumbing used by everything else — settings, caching, market data, Reddit/X clients. | Live |
| `fintwit` | A separate pipeline that archives finance tweets into `data/fintwit.db`. | Live, independent |
| `ticker_digest` | The original idea: summarise YouTube stock videos with AI. | Placeholder, on the roadmap |

---

## A note on the confusing names

This repository has three different names attached to it, for historical
reasons. Nothing is broken — they just never got renamed:

- **The GitHub repo** is called `ticker-video-digest`
- **The installable Python package** is called `ticker-digest`
- **The actual product** is the dashboard, `casino_dashboard`

When something says "ticker digest", it's the old name. When something says
"casino dashboard", it's this. The story is in
[docs/archive/reorg-plan-v1.md](docs/archive/reorg-plan-v1.md).

---

## The key files, if you only remember three

- **[`config/themes.yaml`](config/themes.yaml)** — the list of themes and
  stocks. This *is* the dashboard's universe. Protected file: don't regenerate it.
- **[`STRATEGY.md`](STRATEGY.md)** — why these themes were chosen. Protected file.
- **[`CLAUDE.md`](CLAUDE.md)** — instructions for AI coding assistants working
  in this repo. Read it if you use one.

---

## License

MIT — see [LICENSE](LICENSE).

**Disclaimer:** everything this project produces is aggregated commentary from
public sources. It is not investment advice.
