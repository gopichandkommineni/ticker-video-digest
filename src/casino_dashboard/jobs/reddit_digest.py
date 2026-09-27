"""Daily Reddit digest — a short brief and linked insights per stock, from the
posts ingestion stored in data/reddit.db. Run by `reddit_ingest.yml` right
after ingestion; safe to run by hand.

Uses Gemini's free tier (GEMINI_API_KEY; model: REDDIT_DIGEST_MODEL, default
gemini-flash-lite-latest, Google's alias for the current Flash-Lite model). Without a key
it does nothing and says so.

Usage:
    python -m casino_dashboard.jobs.reddit_digest                 # whole universe
    python -m casino_dashboard.jobs.reddit_digest RKLB ASTS       # these stocks only
    REDDIT_DB_PATH=/tmp/reddit.db python -m casino_dashboard.jobs.reddit_digest RKLB

Writes to data/reddit.db (or REDDIT_DB_PATH) — production data, committed by the
workflow; don't commit a copy from a local run.

In GitHub Actions the report is also appended to $GITHUB_STEP_SUMMARY.
Exit code 1 only when every stock that needed the LLM failed.
"""
import logging
import os
import sys

from core.social_media.reddit.digest import DigestReport, GeminiClient, MissingKey, run_digest
from casino_dashboard.jobs.reddit_ingest import _tickers
from casino_dashboard.jobs.subreddit_catalog_run import load_company_names

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def render(report: DigestReport) -> list[str]:
    icon = {"ok": "✅", "partial": "⚠️", "failed": "❌"}[report.status]
    lines = [
        f"## Reddit digest — {icon} {report.status}",
        "",
        f"{report.digest_date} · model `{report.model}` · {report.calls} LLM calls",
        "",
        f"- Digested: **{len(report.ok)}** stocks, "
        f"**{sum(report.insights.values())}** insights",
        f"- Quiet (no new posts): {len(report.quiet)}",
    ]
    if report.ok:
        lines += ["", "| Stock | Insights |", "|---|---|"]
        lines += [f"| {t} | {report.insights.get(t, 0)} |" for t in report.ok]
    if report.skipped:
        lines += ["", f"⚠️ Stopped early: {report.stopped or 'unknown reason'}",
                  "", f"Not digested today (the next run picks them up): "
                  f"{', '.join(report.skipped)}"]
    if report.failed:
        lines += ["", f"### Failed ({len(report.failed)})", ""]
        lines += [f"- {t}: {e}" for t, e in report.failed.items()]
    return lines


def _emit(text: str) -> None:
    print(text)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(text + "\n")


def main(argv: list[str] | None = None) -> int:
    try:
        llm = GeminiClient()
    except MissingKey:
        _emit("## Reddit digest — skipped\n\nGEMINI_API_KEY is not set, so no digest was "
              "written. Add it as a repository secret to turn the digest on.")
        return 0
    report = run_digest(_tickers(sys.argv[1:] if argv is None else argv), llm,
                        company_names=load_company_names())
    _emit("\n".join(render(report)))
    return 1 if report.status == "failed" else 0


if __name__ == "__main__":
    sys.exit(main())
