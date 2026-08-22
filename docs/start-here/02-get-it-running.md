# 2. Get it running on your own laptop

*Reading time: 10 minutes, most of it waiting for an installer.*

You do **not** need to understand any of the code to do this. Follow the steps
in order and copy-paste the commands exactly.

---

## Before you start: the Terminal

Everything here happens in an app called **Terminal** (on a Mac: press `⌘ Space`,
type "Terminal", press Enter). It's a window where you type commands instead of
clicking buttons.

Three things to know and then we'll move on:

- You type a command and press **Enter**. It runs, prints some text, and gives
  you a fresh prompt when it's finished.
- A command that takes a while may print nothing for a minute. That's normal.
- **`Ctrl+C`** (hold Control, press C) stops whatever is currently running.
  You will use this to shut the dashboard down.

## Step 0 — Do you have Python?

Type this and press Enter:

```bash
python3 --version
```

- **You see `Python 3.11.x` or higher** → you're set, go to Step 1.
- **You see `Python 3.9`, `3.10`, or "command not found"** → install Python
  3.11 or newer from [python.org/downloads](https://www.python.org/downloads/),
  then come back.

## Step 1 — Get the code onto your machine

If someone already put the folder on your laptop, skip to Step 2. Otherwise:

```bash
git clone https://github.com/gopichandkommineni/ticker-video-digest.git
cd ticker-video-digest
```

> Yes, the folder is called `ticker-video-digest` even though the product is a
> dashboard. That's the historical name — see the README.

Every command from here on assumes you are **inside that folder**. If you open
a new Terminal window later, `cd` back into it first.

## Step 2 — Install everything

```bash
./run setup
```

This creates a private Python environment inside the project (a folder called
`.venv`) and downloads the libraries the project depends on. It takes 1–3
minutes and prints a lot of text. You want the last line to say `Installed.`

**If you see `permission denied: ./run`**, run this once and try again:

```bash
chmod +x run
```

## Step 3 — Check that the setup worked

```bash
./run check
```

You should see a list of green ticks:

```
✓ Python environment: Python 3.11.x
✓ Universe config present
✓ Dashboard database present (20M)
✓ .env file present
✓ Universe loads: 12 themes, 64 stocks
```

If anything is a `!` or `✗`, go to
[7. When things break](07-when-things-break.md). Don't push past a broken check.

## Step 4 — Open the dashboard

```bash
./run dashboard
```

Your browser should open by itself at **http://localhost:8501**. If it
doesn't, open that address manually.

You now have the dashboard running. Click through the pages in the left-hand
sidebar. All the data you see was downloaded earlier by the automated job — you
are not calling the internet, you are reading a saved file.

**To stop it:** go back to the Terminal window and press `Ctrl+C`.

---

## Optional: API keys

The dashboard runs fully without any keys. Two features stay switched off until
you add them:

| Feature | Key needed | Where to get it |
|---|---|---|
| Written market thesis on the Market Reality Check page | `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com/) (paid) |
| The real-economy half of the Reality Score | `FRED_API_KEY` | [fred.stlouisfed.org](https://fred.stlouisfed.org/docs/api/api_key.html) (free, instant) |

To add them:

1. Copy the template: `cp .env.example .env`
2. Open `.env` in any text editor.
3. Paste your key after the `=` sign, with no quotes and no spaces:
   `FRED_API_KEY=abcd1234`
4. Save, and restart the dashboard (`Ctrl+C`, then `./run dashboard`).

> 🔐 **Never commit `.env`.** It's already in `.gitignore` so git will ignore
> it, and it must stay that way. Keys are secrets — treat them like passwords.
> The full list of every supported key is in
> [`.env.example`](../../.env.example).

---

## The commands you'll actually use

| Command | What it does |
|---|---|
| `./run dashboard` | Open the dashboard |
| `./run check` | Is my machine set up correctly? |
| `./run test` | Run the automated checks (takes ~1 minute) |
| `./run market` | Print the market report in the Terminal instead of the browser |
| `./run clean` | Delete caches and throwaway files. Always safe. |
| `./run` | Show this menu again |

---

## One rule you must not break

The file `data/snapshots.db` holds the project's real, accumulated history. It
is updated automatically by a robot on GitHub, and committed back to the
repository.

**Never commit your own local version of it.** If you run a data refresh on
your laptop and commit the result, you overwrite months of production history
with partial test data. That's why `./run refresh` writes to a *throwaway* copy
called `data/local-test.db`, which git ignores.

---

**Next:** [3. Tour of the folders →](03-tour-of-the-repo.md)
