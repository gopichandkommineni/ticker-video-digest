# 1. What is this thing?

*Reading time: 6 minutes. No technical background needed.*

---

## The one-sentence version

It's a private web dashboard that watches ~64 hand-picked stocks and tells you,
at a glance, which corners of the market are getting hot.

## The problem it solves

Say you're interested in speculative, story-driven corners of the stock
market — nuclear reactors, rocket launches, quantum computers, the picks-and-
shovels behind AI. There are hundreds of companies, endless news, and endless
opinions on Reddit and X. Checking on all of it by hand is a full-time job, and
most of what you'd read is noise.

This dashboard does the checking for you, on a schedule, and reduces each
company to a handful of numbers you can scan in seconds.

## The idea behind it: "casino-coherent momentum"

That's the project's own phrase, and it means two things stacked together.

**"Casino"** — these are speculative bets, and the project says so out loud
rather than pretending otherwise. Pre-revenue quantum companies and small
rocket builders can double or halve on a single announcement. The dashboard
exists to watch that kind of stock, on purpose.

**"Coherent momentum"** — the belief that these stocks don't move alone. They
move as *themes*. When money rotates into nuclear power, it doesn't pick one
reactor company; it lifts the whole basket. So instead of tracking 64 separate
stories, the dashboard tracks **12 themes**, and asks two questions:

1. Which *theme* is heating up right now?
2. Within that theme, which *stock* is set up to move?

The full reasoning is in [`STRATEGY.md`](../../STRATEGY.md) at the top of the
repository.

## The 12 themes

They live in [`config/themes.yaml`](../../config/themes.yaml), which is the
single source of truth — if that file and this page ever disagree, the file is
right.

| Theme | The story |
|---|---|
| Nuclear | Small modular reactors and the uranium fuel chain |
| Photonics & Optical | The optical-connection bottleneck inside AI data centres |
| Quantum Computing | Pre-revenue computing beyond classical chips |
| Drones & Autonomous Defense | Unmanned systems riding geopolitical tension |
| Space Economy | Launch providers, satellite operators, space comms |
| Critical Minerals | Rare earths and silver; supply chains moving out of China |
| AI Infrastructure | The power, cooling, networking and storage AI runs on |
| Crypto | Listed companies that give stock-market exposure to crypto |
| NeoCloud | Bitcoin miners converting their sites into AI compute |
| Memory | DRAM, NAND flash and storage |
| Network | Network infrastructure and connectivity |
| Orchestration | Software that automates and schedules AI workloads |

> **A wrinkle you'll notice:** `STRATEGY.md` describes 8 themes and ~55 stocks.
> That document was written when the project started; four themes have been
> added since. `config/themes.yaml` — 12 themes, 64 stocks — is the live truth.
> Both files are marked "canonical" and must not be rewritten casually.

## What you actually see on screen

Six pages, listed in the sidebar:

| Page | What it answers |
|---|---|
| **Home** (`app.py`) | One card per theme. Broadest possible overview. |
| **Sector Heat** | Rank the 12 themes against each other on money flow, hype, and growth. |
| **All Tickers** | Every stock in one sortable, filterable table. |
| **Ticker Detail** | Everything known about one stock, on one screen. |
| **Market Reality Check** | Zoom out: is the *whole* stock market priced above what the real economy supports? |
| **Congress** | What US politicians have been buying and selling. |
| **Add Stocks** | A form to add a new stock to the list being watched. |

## What it deliberately does **not** do

- It does not connect to a brokerage, and it cannot buy or sell anything.
- It does not tell you what to buy. It shows numbers; you decide.
- It is not a product for other people. It's one person's research tool, and
  the code is shaped by that — pragmatic, not polished for strangers.

## Who it's for

The repository owner, mainly. If you're reading this, you're being onboarded to
help maintain or extend it.

---

**Next:** [2. Get it running →](02-get-it-running.md)
