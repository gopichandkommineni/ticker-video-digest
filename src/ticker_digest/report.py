"""Render a stored digest run as Markdown.

The CLI renders threads for a terminal. This renders the same run for a place
that understands Markdown — a GitHub Actions job summary, an issue comment, a
pasted note. It reads a run back from JSON rather than re-running the pipeline,
so re-rendering never costs a second model call.

    python -m ticker_digest.report run.json >> "$GITHUB_STEP_SUMMARY"
"""
from __future__ import annotations

import sys
from pathlib import Path

from core.models import DigestRun

_NOVELTY_LABEL = {
    "new": "NEW",
    "developing": "DEVELOPING",
    "known": "KNOWN",
}


def _sources_table(run: DigestRun) -> list[str]:
    lines = [
        "### Sources",
        "",
        "| Score | Channel | Video | Views | Length |",
        "|---|---|---|---:|---:|",
    ]
    for scored in run.videos:
        meta = scored.metadata
        title = meta.title.replace("|", "\\|")
        lines.append(
            f"| {scored.reliability_score:.2f} "
            f"| {meta.channel_title} "
            f"| [{title}]({meta.url}) "
            f"| {meta.view_count:,} "
            f"| {meta.duration_seconds // 60}m |"
        )
    if run.skipped:
        lines.append("")
        for video_id, reason in run.skipped.items():
            lines.append(f"- `{video_id}` skipped — {reason}")
    return lines


def _claims_section(run: DigestRun) -> list[str]:
    if not run.claims:
        return []
    lines = ["### Claims", "", "| Verdict | Sources | Claim |", "|---|---:|---|"]
    for claim in run.claims:
        verdict = _NOVELTY_LABEL.get(claim.novelty, claim.novelty)
        if claim.newly_corroborated:
            verdict += " ✦"
        text = claim.text.replace("|", "\\|")
        lines.append(f"| `{verdict}` | {claim.source_count} | {text} |")
    if any(c.newly_corroborated for c in run.claims):
        lines += ["", "✦ — already on record, but repeated by a channel that never said it before."]
    return lines


def thread_to_markdown(run: DigestRun) -> str:
    """Render *run* as a Markdown report.

    Runs that produced no thread still render: what was searched, what was
    dropped and why is the useful part of an empty run.
    """
    ticker = run.request.ticker
    company = run.request.company_name
    source = run.channel.title if run.channel else "YouTube search"

    lines = [f"## {ticker} — {company}", ""]

    if not run.videos:
        if not run.considered_candidates:
            lines.append(
                f"YouTube returned nothing at all for **{ticker}** from {source} "
                f"in the last {run.request.days} days."
            )
        else:
            lines += [
                (
                    f"Found {run.considered_candidates} videos about **{ticker}** "
                    f"from {source} in the last {run.request.days} days, but none "
                    "passed the quality filters:"
                ),
                "",
                *(
                    f"- {count} {reason}"
                    for reason, count in sorted(
                        run.filtered.items(), key=lambda kv: -kv[1]
                    )
                ),
            ]
        lines += ["", "Nothing was transcribed and no model calls were made."]
        return "\n".join(lines)

    thread = run.thread
    if thread is not None:
        corroborated = sum(1 for c in run.claims if c.newly_corroborated)
        meta = (
            f"{thread.video_count} videos · {thread.new_claim_count} new "
            f"of {len(run.claims)} claims"
        )
        if corroborated:
            meta += f" · {corroborated} newly corroborated"
        meta += f" · sentiment: {thread.overall_sentiment}"
        lines += [
            f"**{thread.headline}**",
            "",
            meta,
            "",
            (
                f"`thread {thread.thread_id}` · source: {source} · "
                f"{thread.generated_at:%Y-%m-%d %H:%M} UTC"
            ),
            "",
        ]

    lines += _sources_table(run) + [""]

    if thread is None:
        lines += [
            "### No thread",
            "",
            "No transcript could be analysed, so there was nothing to synthesise.",
        ]
        return "\n".join(lines)

    lines += _claims_section(run) + [""]
    lines += ["### Thread", ""]
    for post in thread.posts:
        label = _NOVELTY_LABEL.get(post.novelty, post.novelty)
        lines += [f"**{post.position}. `{label}` {post.headline}**", "", post.body, ""]
        for citation in post.citations:
            paraphrase = citation.quote_paraphrase.strip()
            lines.append(f"> [{paraphrase}]({citation.url})")
        lines.append("")

    lines += ["---", "", f"_{thread.disclaimer}_"]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 1:
        print("usage: python -m ticker_digest.report <run.json|->", file=sys.stderr)
        return 2

    raw = sys.stdin.read() if argv[0] == "-" else Path(argv[0]).read_text()
    print(thread_to_markdown(DigestRun.model_validate_json(raw)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
