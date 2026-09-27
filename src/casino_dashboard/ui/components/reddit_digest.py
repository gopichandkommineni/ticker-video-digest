"""'What Reddit is saying' — the Reddit digest on the Ticker Detail page.

Latest digest first: a mood chip and the one-paragraph brief, then the insight
list — headline, detail, and under each the clickable posts it came from.
Earlier days sit in an expander. Text comes from Reddit and an LLM, so it is
escaped before it reaches Markdown.
"""
import re

import streamlit as st

from core.social_media.reddit.digest import Digest, Insight

_MOOD = {
    "bullish": ("🟢", "Bullish chatter"),
    "bearish": ("🔴", "Bearish chatter"),
    "mixed": ("🟡", "Mixed chatter"),
    "neutral": ("⚪", "Neutral chatter"),
}
_KIND = {
    "contract": "Contract", "product": "Product / release", "earnings": "Earnings",
    "guidance": "Guidance", "partnership": "Partnership", "regulatory": "Regulatory",
    "analyst": "Analyst", "thesis": "Thesis", "risk": "Risk", "rumor": "Rumor",
    "other": "Other",
}
_STANCE = {  # arrow + Streamlit colour, so a bearish item never reads as good news
    "bullish": ("▲", "green"), "bearish": ("▼", "red"), "neutral": ("•", "gray"),
}

DISCLAIMER = (
    "AI-written summary of public Reddit posts — it can be wrong or miss things. "
    "Read the linked posts before relying on anything here. Not investment advice."
)


def md_escape(text: str) -> str:
    """Neutralise Markdown so post titles and model text render as plain text."""
    return re.sub(r"([\\`*_{}\[\]()#+\-!|>~<$])", r"\\\1", text)


def _safe_url(url: str) -> str:
    """Keep a URL intact inside a Markdown link's parentheses."""
    return url.replace(" ", "%20").replace("(", "%28").replace(")", "%29")


def _short(text: str, n: int) -> str:
    text = " ".join(text.split())
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def insight_markdown(ins: Insight) -> str:
    """One insight: tagged headline, detail, then a line of source links."""
    arrow, colour = _STANCE.get(ins.stance, _STANCE["neutral"])
    tag = f":{colour}[{arrow} {_KIND.get(ins.kind, 'Other')}]"
    links = " · ".join(
        f"[r/{md_escape(s.subreddit)}: {md_escape(_short(s.title, 70))} ↗]({_safe_url(s.url)})"
        for s in ins.sources if s.url.startswith("https://")
    )
    text = f"**{md_escape(ins.headline)}** — {tag}  \n{md_escape(ins.detail)}"
    return f"{text}  \n{links}" if links else text


def header_markdown(d: Digest) -> str:
    icon, label = _MOOD.get(d.mood or "", ("⚪", "Chatter"))
    if d.status == "quiet":
        return f"_{md_escape(d.summary)}_"
    return f"{icon} **{label}.** {md_escape(d.summary)}"


def render_reddit_digest(digests: list[Digest]) -> None:
    """Render the section body. *digests* is newest first (see load_recent)."""
    if not digests:
        st.caption("No Reddit digest yet — it appears after the daily Reddit job runs "
                   "for this stock.")
        return
    shown = [d for d in digests if d.status in ("ok", "quiet")]
    if not shown:
        st.caption("The latest Reddit digest failed; it will be retried on the next run.")
        return

    latest = shown[0]
    st.markdown(header_markdown(latest))
    meta = f"{latest.digest_date}"
    if latest.status == "ok":
        meta += f" · from {latest.posts_considered} new posts · summarised by {latest.model}"
    st.caption(meta)
    if latest.status == "ok" and not latest.insights:
        st.caption("Nothing specific enough to list as an insight today.")
    for ins in latest.insights:
        st.markdown(insight_markdown(ins))

    earlier = [d for d in shown[1:] if d.status == "ok"]
    if earlier:
        count = sum(len(d.insights) for d in earlier)
        with st.expander(f"Earlier this week · {len(earlier)} digests · {count} insights"):
            for d in earlier:
                st.markdown(f"**{d.digest_date}** — {header_markdown(d)}")
                for ins in d.insights:
                    st.markdown(insight_markdown(ins))
    st.caption(DISCLAIMER)
