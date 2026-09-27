#!/usr/bin/env bash
#
# reddit_brief_local.sh — write the daily Reddit brief on your own computer,
# with Claude Code on your Claude subscription (no API key, no API bill).
#
#   ./run reddit-brief RKLB [ASTS…] On demand: fetch these stocks' last 7 days of Reddit
#                                  posts, have Claude analyse them, publish the insights.
#                                  (--days N for a different window.)
#   ./run reddit-brief check       Check the prerequisites; walks you through any that are missing.
#   ./run reddit-brief install     Check, then schedule the job. The one command you need.
#   ./run reddit-brief status      Is it scheduled? When did it last run?
#   ./run reddit-brief run         Run it now (normally the scheduler does this).
#   ./run reddit-brief uninstall   Stop running it.
#
# How it works: GitHub Actions still collects the Reddit posts every day into
# data/reddit.db on main. This job, run by your computer's scheduler every hour
# while it's on (and at start-up), checks whether a new collection has landed
# since the last brief. If so, it:
#   1. updates its own private copy of the repository (never your working copy);
#   2. writes each stock's digest with `claude -p` on your login;
#   3. merges only the new digest rows into the latest data/reddit.db from main,
#      commits that file and pushes it — so posts collected meanwhile are kept.
# If nothing new has landed it does nothing, so it spends none of your plan.
#
# The private copy is small on purpose: the repository also commits two ~30 MB
# databases several times a day, so its full history is several GB. The copy is
# shallow (latest commit only), fetches file contents on demand, and checks out
# only what the digest needs (code, config/, data/reddit.db — not research/). An hourly check
# downloads a few KB unless data/reddit.db actually changed.
#
# Works on macOS (launchd) and Linux (systemd user timer, or cron). Everything
# lives in ~/.local/share/ticker-reddit-brief (override with TICKER_BRIEF_HOME).
# See docs/runbooks/reddit-local-runbook.md §5e.
set -euo pipefail
export GIT_TERMINAL_PROMPT=0     # never hang on a password prompt; use a credential helper

HOME_DIR="${TICKER_BRIEF_HOME:-$HOME/.local/share/ticker-reddit-brief}"
CLONE="$HOME_DIR/repo"
LOGS="$HOME_DIR/logs"
CONF="$HOME_DIR/config"
STAMP="$HOME_DIR/last_digested_ingest"
SEEN="$HOME_DIR/last_seen_reddit_db"
ERRORS="$LOGS/errors.jsonl"            # why outside calls failed: one JSON line each   # git object id of data/reddit.db last looked at
LOCK="$HOME_DIR/lock"
BIN="$HOME_DIR/bin/reddit-brief.sh"
LABEL="com.ticker-video-digest.reddit-brief"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
UNIT_DIR="$HOME/.config/systemd/user"
CRON_TAG="# ticker-reddit-brief"
DIGEST_CODE="src/core/social_media/reddit/digest/claude_cli.py"

bold() { printf '\033[1m%s\033[0m\n' "$1"; }
ok()   { printf '\033[32m✓\033[0m %s\n' "$1"; }
warn() { printf '\033[33m!\033[0m %s\n' "$1"; }
bad()  { printf '\033[31m✗\033[0m %s\n' "$1"; }
die()  { bad "$1" >&2; exit 1; }
log()  { printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"; }

# Saved at install time: where to clone from, which branch, and the PATH that
# found claude/uv (schedulers start jobs with a bare PATH).
load_conf() {
  ORIGIN_URL="" REF="main" SAVED_PATH="" TICKERS=""
  # shellcheck disable=SC1090
  [ -f "$CONF" ] && . "$CONF"
  REF="${TICKER_BRIEF_REF:-$REF}"
  [ -n "$SAVED_PATH" ] && export PATH="$SAVED_PATH"
  return 0
}

interactive() { [ -t 0 ] && [ -t 1 ]; }

# Keep asking until a prerequisite is met.
#   require "what" check_fn "how to fix it" [command that fixes it]
# "how to fix it" may also name a function that prints the instructions.
require() {
  local what="$1" check="$2" how="$3" fix="${4:-}"
  while ! "$check"; do
    bad "$what"
    if declare -F "$how" >/dev/null; then "$how"; else printf '%b\n' "$how"; fi | sed 's/^/    /'
    interactive || die "Fix the above, then run this again."
    if [ -n "$fix" ]; then
      printf '    Do this for you now? [y/N] '
      read -r answer
      if [[ "$answer" =~ ^[Yy] ]]; then
        bash -c "$fix" || warn "That didn't work — follow the steps above by hand."
        hash -r
        continue
      fi
    fi
    printf '    Press Enter when done to check again (or type q to quit): '
    read -r answer
    [[ "$answer" =~ ^[Qq] ]] && exit 1
    hash -r
  done
  ok "$what"
}

# --- the checks -------------------------------------------------------------------

has_supported_os() { case "$(uname -s)" in Darwin|Linux) return 0 ;; *) return 1 ;; esac; }
has_git()    { command -v git >/dev/null 2>&1; }
has_python() {
  command -v uv >/dev/null 2>&1 && return 0
  command -v python3 >/dev/null 2>&1 &&
    python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null
}
has_claude() { command -v claude >/dev/null 2>&1; }

CLAUDE_CHECKED=""
claude_signed_in() {
  [ -n "$CLAUDE_CHECKED" ] && return 0
  local out
  # Same as the job: API-key variables removed, so this proves the
  # subscription login works on its own.
  out="$(env -u ANTHROPIC_API_KEY -u ANTHROPIC_AUTH_TOKEN \
          claude -p --output-format json --model haiku --tools "" \
          --no-session-persistence "Reply with just the word OK" </dev/null 2>&1)" || true
  if printf '%s' "$out" | grep -q '"is_error":false'; then
    CLAUDE_CHECKED=1
    return 0
  fi
  CLAUDE_ERR="$(printf '%s' "$out" | tail -c 300)"
  return 1
}
how_claude_login() {
  echo "In another terminal, run:  claude"
  echo "Sign in with your Claude Pro/Max account (type /login if it doesn't ask),"
  echo "then type /exit. The job never uses an API key, so this login is what it runs on."
  echo "(Claude said: ${CLAUDE_ERR:-no answer})"
}

has_clone() { [ -d "$CLONE/.git" ]; }
main_has_code() {
  fetch_main 2>/dev/null &&
    [ -n "$(git -C "$CLONE" ls-tree --name-only "origin/$REF" -- "$DIGEST_CODE")" ]
}
can_push() { git -C "$CLONE" push --dry-run -q origin "HEAD:$REF" >/dev/null 2>&1; }

cmd_check() {
  load_conf
  bold "Checking what the daily Reddit brief needs on this computer…"
  require "macOS or Linux" has_supported_os \
    "This scheduler supports macOS and Linux only.\nOn Windows, install WSL (Ubuntu) and run this inside it."
  require "git is installed" has_git \
    "Install git:\n  macOS:  xcode-select --install\n  Linux:  sudo apt install git   (or your distribution's package manager)"
  require "uv (or Python 3.11+) is installed" has_python \
    "Install uv, the Python installer this project uses:\n  curl -LsSf https://astral.sh/uv/install.sh | sh\nThen open a new terminal (so it's on your PATH)." \
    "curl -LsSf https://astral.sh/uv/install.sh | sh"
  # The uv installer puts it in ~/.local/bin, which may not be on PATH yet.
  [ -x "$HOME/.local/bin/uv" ] && export PATH="$HOME/.local/bin:$PATH"
  require "Claude Code is installed (the \`claude\` command)" has_claude \
    "Install Claude Code — see https://docs.claude.com/en/docs/claude-code/setup\n  With Node.js 18+:  npm install -g @anthropic-ai/claude-code\nThen open a new terminal and come back."
  CLAUDE_ERR=""
  require "Claude Code is signed in to your Claude subscription" claude_signed_in how_claude_login
  prepare_clone
  require "The repository's main branch has the Claude digest code" main_has_code \
    "origin/$REF doesn't have $DIGEST_CODE yet.\nMerge the pull request that adds it (PR #154), then check again."
  require "You can push to GitHub from this computer" can_push \
    "The job pushes data/reddit.db to $REF, so git needs your GitHub login.\nEasiest: install the GitHub CLI and run:  gh auth login\n(choose HTTPS and 'Login with a web browser'), then:  gh auth setup-git\nOr set up an SSH key: https://docs.github.com/en/authentication/connecting-to-github-with-ssh"
  ok "Everything the brief needs is in place."
}

# --- the private copy of the repository --------------------------------------------

prepare_clone() {
  mkdir -p "$HOME_DIR" "$LOGS" "$(dirname "$BIN")"
  if [ -z "$ORIGIN_URL" ]; then
    local here
    here="$(cd "$(dirname "$0")/.." && pwd)"
    ORIGIN_URL="$(git -C "$here" remote get-url origin 2>/dev/null || true)"
    [ -n "$ORIGIN_URL" ] || die "Run this from inside the project folder (couldn't find its GitHub address)."
  fi
  # A copy left half-made by an interrupted install: start again.
  if [ -d "$CLONE" ] && ! git -C "$CLONE" rev-parse -q --verify HEAD >/dev/null 2>&1; then
    rm -rf "$CLONE"
  fi
  if ! has_clone; then
    log "Making a small private copy of the repository in $CLONE (your own folder is never touched)…"
    git clone --depth 1 --filter=blob:none --no-checkout --single-branch --branch "$REF" \
      "$ORIGIN_URL" "$CLONE"
    # Everything except research/ and the big databases in data/; of data/,
    # only reddit.db.
    git -C "$CLONE" sparse-checkout set --no-cone '/*' '!/research/' '!/data/*' '/data/reddit.db'
    git -C "$CLONE" checkout -q "$REF"
  fi
  git -C "$CLONE" config user.name "reddit-brief-local"
  git -C "$CLONE" config user.email "bot@users.noreply.github.com"
  ok "Private copy of the repository: $CLONE"
}

install_deps() {
  local stamp="$CLONE/.venv/.pyproject-sha" sha
  sha="$(git -C "$CLONE" rev-parse HEAD:pyproject.toml)"
  [ -x "$CLONE/.venv/bin/python" ] && [ "$(cat "$stamp" 2>/dev/null)" = "$sha" ] && return 0
  log "Installing the project's Python packages…"
  if command -v uv >/dev/null 2>&1; then
    (cd "$CLONE" && uv venv -q --python 3.11 .venv 2>/dev/null || true
     uv pip install -q --python .venv/bin/python -e .)
  else
    (cd "$CLONE" && { [ -d .venv ] || python3 -m venv .venv; } &&
     .venv/bin/python -m pip install -q -e .)
  fi
  echo "$sha" > "$stamp"
}

# --- the job ------------------------------------------------------------------------

# Newest main: latest commit only, no file contents until they're needed.
fetch_main() {
  git -C "$CLONE" fetch -q --depth 1 --filter=blob:none origin "$REF"
}

# Publish only the new digest rows from $1 (a scratch reddit.db), merged onto the
# newest data/reddit.db on main; commit with message $2 and push. If main moved
# meanwhile, merge again (up to 4 tries). Returns 1 if it never got through.
publish_digests() {
  local work="$1" message="$2" db="$CLONE/data/reddit.db" attempt
  for attempt in 1 2 3 4; do
    fetch_main
    git -C "$CLONE" reset -q --hard "origin/$REF"
    (cd "$CLONE" && py_env .venv/bin/python -m casino_dashboard.jobs.reddit_digest_merge "$work" "$db")
    git -C "$CLONE" add -- data/reddit.db
    if git -C "$CLONE" diff --cached --quiet; then
      log "No new digests to publish."
      return 0
    fi
    git -C "$CLONE" commit -q -m "$message: $(date -u +%Y-%m-%dT%H:%M)Z"
    if git -C "$CLONE" push -q origin "HEAD:$REF"; then
      log "Published to $REF."
      return 0
    fi
    log "Push was rejected (main moved on) — merging again (attempt $attempt)…"
    sleep $((attempt * 10))
  done
  return 1
}

take_lock() {
  if ! mkdir "$LOCK" 2>/dev/null; then
    # A run that died without cleaning up leaves the lock; ignore it after 3 hours.
    if [ -n "$(find "$LOCK" -maxdepth 0 -mmin +180 2>/dev/null)" ]; then
      rmdir "$LOCK" 2>/dev/null || true
      mkdir "$LOCK" || return 1
    else
      return 1                            # another run is going
    fi
  fi
  trap 'rmdir "$LOCK" 2>/dev/null || true' EXIT
}

# The error log keeps its newest 1,000 lines.
trim_errors() {
  if [ -f "$ERRORS" ] && [ "$(wc -l <"$ERRORS")" -gt 1000 ]; then
    tail -n 1000 "$ERRORS" >"$ERRORS.tmp" && mv "$ERRORS.tmp" "$ERRORS"
  fi
  return 0
}

# The last N failures from the error log, one readable line each.
show_errors() {
  local n="${1:-5}" since="${2:-}"
  [ -s "$ERRORS" ] || return 0
  "$CLONE/.venv/bin/python" - "$ERRORS" "$n" "$since" <<'PY' 2>/dev/null || tail -n "$n" "$ERRORS"
import json, sys
path, n, since = sys.argv[1], int(sys.argv[2]), sys.argv[3]
rows = []
for line in open(path, encoding="utf-8").read().splitlines():
    try:
        r = json.loads(line)
    except ValueError:
        continue
    if not since or r.get("at", "") >= since:
        rows.append(r)
for r in rows[-n:]:
    ctx = ", ".join(f"{k}={v}" for k, v in r.get("context", {}).items())
    status = r.get("status") or "no response"
    print(f"    {r.get('at', '')}  {r.get('source', '')} [{status}] {r.get('reason') or '(no reason given)'}")
    if ctx:
        print(f"        ↳ {ctx}")
PY
}

# Keep the private copy small: drop what older fetches left behind.
compact_clone() {
  git -C "$CLONE" reflog expire --expire=now --all 2>/dev/null || true
  git -C "$CLONE" gc -q --prune=now 2>/dev/null || true
}

# The newest finished ingest in a reddit.db ("" if none).
latest_ingest() {
  "$CLONE/.venv/bin/python" - "$1" <<'PY'
import sqlite3, sys
try:
    row = sqlite3.connect(sys.argv[1]).execute(
        "SELECT max(finished_at) FROM runs WHERE finished_at IS NOT NULL").fetchone()
    print(row[0] or "")
except sqlite3.Error:
    print("")
PY
}

# Stand-ins so the shared config module imports; the digest never uses them.
py_env() {
  env REDDIT_DIGEST_LLM=claude REDDIT_ERROR_LOG="$ERRORS" \
      YOUTUBE_API_KEY="${YOUTUBE_API_KEY:-unused-by-reddit-brief}" \
      ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-unused-by-reddit-brief}" "$@"
}

cmd_run() {
  local force=""
  [ "${1:-}" = "--force" ] && force=1
  load_conf
  [ -d "$CLONE/.git" ] || die "Not set up yet. Run:  ./run reddit-brief install"
  mkdir -p "$LOGS"
  take_lock || exit 0                     # another run is going
  trim_errors
  local logfile="$LOGS/$(date -u +%Y-%m-%d).log"
  find "$LOGS" -name '*.log' -mtime +30 -delete 2>/dev/null || true
  exec >>"$logfile" 2>&1

  log "Checking for new Reddit data on ${REF}…"
  fetch_main
  local blob
  blob="$(git -C "$CLONE" rev-parse -q --verify "origin/$REF:data/reddit.db" 2>/dev/null || true)"
  if [ -z "$blob" ]; then
    log "No data/reddit.db on $REF yet — GitHub's Reddit ingest hasn't run. Nothing to do."
    return 0
  fi
  if [ -z "$force" ] && [ "$blob" = "$(cat "$SEEN" 2>/dev/null)" ]; then
    log "data/reddit.db hasn't changed since the last check. Nothing to do."
    return 0
  fi
  git -C "$CLONE" reset -q --hard "origin/$REF"
  install_deps
  local db="$CLONE/data/reddit.db"
  local ingest
  ingest="$(latest_ingest "$db")"
  if [ -z "$force" ] && [ -n "$ingest" ] && [ "$ingest" = "$(cat "$STAMP" 2>/dev/null)" ]; then
    log "Already digested the latest collection ($ingest). Nothing to do."
    echo "$blob" > "$SEEN"
    return 0
  fi

  local work="$HOME_DIR/work.db" out="$HOME_DIR/last_report.md"
  cp "$db" "$work"
  log "Writing the brief with Claude Code (collection finished $ingest)…"
  # shellcheck disable=SC2086
  (cd "$CLONE" && py_env REDDIT_DB_PATH="$work" \
     .venv/bin/python -m casino_dashboard.jobs.reddit_digest $TICKERS) | tee "$out" || true

  publish_digests "$work" "Reddit digest (local, Claude subscription)" ||
    { log "Couldn't publish after 4 attempts; the next run will try again."; return 1; }

  if grep -q "Stopped early" "$out"; then
    # e.g. the plan's usage limit: try again at the next hourly check.
    log "Stopped early — will retry on the next check."
  else
    [ -n "$ingest" ] && echo "$ingest" > "$STAMP"
    git -C "$CLONE" rev-parse -q --verify "HEAD:data/reddit.db" > "$SEEN" 2>/dev/null || true
    log "Done."
  fi
  compact_clone
}

# --- on demand ----------------------------------------------------------------------

cmd_now() {
  local days=7 tickers=() arg
  while [ $# -gt 0 ]; do
    case "$1" in
      --days) days="${2:?--days needs a number}"; shift 2 ;;
      --days=*) days="${1#--days=}"; shift ;;
      -*) die "Unknown option: $1" ;;
      *) tickers+=("$(printf '%s' "$1" | tr '[:lower:]' '[:upper:]')"); shift ;;
    esac
  done
  [ ${#tickers[@]} -gt 0 ] || die "Which stock? For example:  ./run reddit-brief RKLB"
  [[ "$days" =~ ^[0-9]+$ ]] && [ "$days" -ge 1 ] || die "--days must be a whole number of days"
  load_conf
  if ! has_clone; then
    warn "First time here — checking what this needs first."
    cmd_check
  fi
  mkdir -p "$LOGS"
  take_lock || die "Another Reddit brief run is going. Try again in a few minutes."
  local logfile="$LOGS/$(date -u +%Y-%m-%d).log" started
  started="$(date -u +%Y-%m-%dT%H:%M:%S)"
  trim_errors
  bold "Reddit brief for ${tickers[*]} — last $days days"

  log "Updating the private copy…"
  fetch_main
  git -C "$CLONE" reset -q --hard "origin/$REF"
  install_deps
  local work="$HOME_DIR/on-demand.db" out="$HOME_DIR/last_report.md"
  rm -f "$work"
  [ -f "$CLONE/data/reddit.db" ] && cp "$CLONE/data/reddit.db" "$work"

  log "Fetching the last $days days of Reddit posts for ${tickers[*]}…"
  if ! (cd "$CLONE" && py_env REDDIT_DB_PATH="$work" \
        .venv/bin/python -m casino_dashboard.jobs.reddit_ingest --days "$days" "${tickers[@]}") \
        2>&1 | tee -a "$logfile" | { grep -vE '^[0-9-]+ [0-9:,]+ (INFO|DEBUG|WARNING)' || true; }; then
    die "Couldn't fetch Reddit posts (is the Reddit archive reachable?). Details: $logfile"
  fi

  log "Asking Claude to analyse them (about a minute per stock)…"
  (cd "$CLONE" && py_env REDDIT_DB_PATH="$work" \
     .venv/bin/python -m casino_dashboard.jobs.reddit_digest --days "$days" --show "${tickers[@]}") \
     2>>"$logfile" | tee "$out" || true
  grep -q "Stopped early" "$out" && warn "Claude stopped early (see above) — publishing what was done."
  if [ -s "$ERRORS" ] && [ -n "$(show_errors 1 "$started")" ]; then
    warn "Some calls failed on this run. Refused searches were retried other ways (see the report); the reasons, newest last (all: $ERRORS):"
    show_errors 8 "$started"
  fi

  log "Publishing to the dashboard's database on ${REF}…"
  publish_digests "$work" "Reddit brief on demand (${tickers[*]}, ${days}d, Claude subscription)" \
    2>&1 | tee -a "$logfile" ||
    die "Couldn't publish (git push kept failing). Your insights are in $work; try again."
  compact_clone
  ok "Done. They show on each stock's Ticker Detail page under \"What Reddit is saying\" once the dashboard picks up main."
}

# --- scheduling ------------------------------------------------------------------------

schedule_macos() {
  mkdir -p "$(dirname "$PLIST")"
  cat >"$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array><string>/bin/bash</string><string>$BIN</string><string>run</string></array>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key><string>$PATH</string>
    <key>TICKER_BRIEF_HOME</key><string>$HOME_DIR</string>
  </dict>
  <key>RunAtLoad</key><true/>
  <key>StartInterval</key><integer>3600</integer>
  <key>StandardOutPath</key><string>$LOGS/scheduler.log</string>
  <key>StandardErrorPath</key><string>$LOGS/scheduler.log</string>
</dict>
</plist>
EOF
  launchctl bootout "gui/$(id -u)" "$PLIST" 2>/dev/null || true
  launchctl bootstrap "gui/$(id -u)" "$PLIST"
  ok "Scheduled with launchd: at log-in, then every hour while the Mac is on."
}

schedule_linux() {
  if command -v systemctl >/dev/null 2>&1 && systemctl --user show-environment >/dev/null 2>&1; then
    mkdir -p "$UNIT_DIR"
    cat >"$UNIT_DIR/reddit-brief.service" <<EOF
[Unit]
Description=Daily Reddit brief (Claude Code on your subscription)

[Service]
Type=oneshot
Environment=PATH=$PATH
Environment=TICKER_BRIEF_HOME=$HOME_DIR
ExecStart=/bin/bash $BIN run
EOF
    cat >"$UNIT_DIR/reddit-brief.timer" <<EOF
[Unit]
Description=Check for new Reddit data hourly and write the brief

[Timer]
OnStartupSec=3min
OnUnitActiveSec=1h

[Install]
WantedBy=timers.target
EOF
    systemctl --user daemon-reload
    systemctl --user enable --now reddit-brief.timer >/dev/null
    ok "Scheduled with systemd: 3 minutes after log-in, then every hour."
    warn "It runs while you're logged in. To run it from start-up without logging in:  sudo loginctl enable-linger $USER"
  else
    command -v crontab >/dev/null 2>&1 ||
      die "No scheduler found (no systemd user session, no cron). Install cron — e.g. sudo apt install cron — and run this again."
    local line1="@reboot sleep 180 && PATH='$PATH' TICKER_BRIEF_HOME='$HOME_DIR' /bin/bash '$BIN' run $CRON_TAG"
    local line2="17 * * * * PATH='$PATH' TICKER_BRIEF_HOME='$HOME_DIR' /bin/bash '$BIN' run $CRON_TAG"
    { crontab -l 2>/dev/null | grep -v "$CRON_TAG" || true; echo "$line1"; echo "$line2"; } | crontab -
    ok "Scheduled with cron: at start-up, then every hour."
  fi
}

cmd_install() {
  cmd_check
  load_conf
  [ -n "$ORIGIN_URL" ] || ORIGIN_URL="$(git -C "$CLONE" remote get-url origin)"
  install_deps
  cp "$0" "$BIN"
  chmod +x "$BIN"
  cat >"$CONF" <<EOF
ORIGIN_URL='$ORIGIN_URL'
REF='$REF'
SAVED_PATH='$PATH'
TICKERS='${TICKERS:-}'
EOF
  case "$(uname -s)" in
    Darwin) schedule_macos ;;
    Linux) schedule_linux ;;
  esac
  echo
  bold "All set."
  echo "Whenever this computer is on, it checks every hour for new Reddit data and,"
  echo "once a day when GitHub has collected new posts, writes the brief with Claude."
  echo "  Status:   ./run reddit-brief status"
  echo "  Run now:  ./run reddit-brief run"
  echo "  Stop:     ./run reddit-brief uninstall"
  echo "  Logs:     $LOGS"
  if interactive; then
    printf 'Write the first brief now? It takes about a minute per stock with new posts. [y/N] '
    read -r answer
    if [[ "$answer" =~ ^[Yy] ]]; then
      "$BIN" run --force || true
      cmd_status
    fi
  fi
}

cmd_uninstall() {
  case "$(uname -s)" in
    Darwin)
      launchctl bootout "gui/$(id -u)" "$PLIST" 2>/dev/null || true
      rm -f "$PLIST" ;;
    Linux)
      if [ -f "$UNIT_DIR/reddit-brief.timer" ]; then
        systemctl --user disable --now reddit-brief.timer 2>/dev/null || true
        rm -f "$UNIT_DIR/reddit-brief.service" "$UNIT_DIR/reddit-brief.timer"
        systemctl --user daemon-reload 2>/dev/null || true
      fi
      if crontab -l 2>/dev/null | grep -q "$CRON_TAG"; then
        { crontab -l | grep -v "$CRON_TAG" || true; } | crontab -
      fi ;;
  esac
  ok "No longer scheduled."
  if interactive && [ -d "$HOME_DIR" ]; then
    printf 'Also delete %s (its private repo copy and logs)? [y/N] ' "$HOME_DIR"
    read -r answer
    [[ "$answer" =~ ^[Yy] ]] && rm -rf "$HOME_DIR" && ok "Deleted."
  fi
  return 0
}

cmd_status() {
  load_conf
  bold "Daily Reddit brief — status"
  case "$(uname -s)" in
    Darwin) launchctl print "gui/$(id -u)/$LABEL" >/dev/null 2>&1 &&
              ok "Scheduled (launchd)" || warn "Not scheduled — run:  ./run reddit-brief install" ;;
    Linux)
      if systemctl --user is-enabled reddit-brief.timer >/dev/null 2>&1; then ok "Scheduled (systemd timer)"
      elif crontab -l 2>/dev/null | grep -q "$CRON_TAG"; then ok "Scheduled (cron)"
      else warn "Not scheduled — run:  ./run reddit-brief install"; fi ;;
  esac
  if [ -f "$STAMP" ]; then ok "Last collection digested: $(cat "$STAMP")"; else warn "No brief written yet"; fi
  if [ -s "$ERRORS" ]; then
    echo
    echo "Latest failed calls and why ($ERRORS):"
    show_errors 5
  fi
  local latest
  latest="$(ls -1 "$LOGS"/20*.log 2>/dev/null | tail -1 || true)"
  if [ -n "$latest" ]; then
    echo
    echo "Latest log ($latest):"
    tail -n 15 "$latest" | sed 's/^/    /'
  fi
}

case "${1:-help}" in
  now) shift; cmd_now "$@" ;;
  check) cmd_check ;;
  install) cmd_install ;;
  run) shift; cmd_run "$@" ;;
  status) cmd_status ;;
  uninstall) cmd_uninstall ;;
  help|-h|--help) sed -n '3,13p' "$0" | sed 's/^# \{0,1\}//' ;;
  *) cmd_now "$@" ;;                      # ./run reddit-brief RKLB …
esac
