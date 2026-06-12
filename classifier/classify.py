"""
Zero-cost hierarchical tweet classifier.

Architecture:
  1. Load taxonomy.yaml — keyword corpus for every (theme, sub_theme)
  2. For each tweet: score against every sub_theme keyword set
  3. Assign all sub_themes above MIN_SCORE threshold (multi-label)
  4. Tickers extracted from the tweet inherit all matched (theme, sub_theme) pairs
  5. Output: per-ticker classification with evidence trail

No LLM. No API. Pure keyword matching with weighted scoring.
"""

import re
import json
import yaml
from pathlib import Path
from collections import defaultdict
from dataclasses import dataclass, field

# ── config ────────────────────────────────────────────────────────────────────
TAXONOMY_PATH = Path(__file__).parent / "taxonomy.yaml"
MIN_SCORE = 3          # minimum score to claim a sub_theme match
TICKER_RE  = re.compile(r'\$([A-Z]{1,5})(?=[^A-Z]|$)')
CURRENCY_RE = re.compile(r'\$\d')   # $100M, $3.6B — not tickers

FALSE_POSITIVES = {
    "I","A","US","AI","IPO","CEO","CFO","EPS","PE","ETF",
    "AM","PM","GDP","CPI","FY","Q","S","P","VC","DC",
    "OK","OR","IF","IT","AT","BY","IN","ON","BE","DO",
    "GO","IS","OF","AS","UP","NO","SO","TO","VS",
}

# ── data structures ────────────────────────────────────────────────────────────
@dataclass
class SubThemeMatch:
    theme: str
    sub_theme: str
    score: int
    matched_keywords: list[str]

@dataclass
class TweetClassification:
    tweet_id: str
    handle: str
    date: str
    text: str
    tickers: list[str]
    matches: list[SubThemeMatch]   # tweet-level matches, ordered by score desc
    ticker_matches: dict = field(default_factory=dict)  # ticker -> proximity-scored matches


# ── taxonomy loader ────────────────────────────────────────────────────────────
def load_taxonomy(path: Path) -> dict:
    """
    Returns:
      {
        sub_theme_key: {
          "theme": str,
          "sub_theme": str,
          "patterns": [(compiled_regex, weight), ...]
        }
      }
    """
    with open(path) as f:
        raw = yaml.safe_load(f)

    taxonomy = {}
    for theme_key, theme_data in raw["themes"].items():
        theme_name = theme_data["theme"]
        for sub_key, sub_data in theme_data["sub_themes"].items():
            patterns = []
            for entry in sub_data["keywords"]:
                kw, weight = entry[0], entry[1]
                # multi-word phrases need special care: match as substring
                # single words: use word boundary
                if " " in kw:
                    pat = re.compile(re.escape(kw), re.IGNORECASE)
                else:
                    pat = re.compile(r'\b' + re.escape(kw) + r'\b', re.IGNORECASE)
                patterns.append((pat, weight))

            taxonomy[f"{theme_key}__{sub_key}"] = {
                "theme": theme_name,
                "sub_theme": sub_key.replace("_", " "),
                "patterns": patterns,
            }
    return taxonomy


# ── scoring ────────────────────────────────────────────────────────────────────
def score_text(text: str, taxonomy: dict) -> list[SubThemeMatch]:
    """Score a text blob against all sub_themes. Return all matches >= MIN_SCORE."""
    matches = []
    for key, sub in taxonomy.items():
        score = 0
        hit_keywords = []
        for (pat, weight) in sub["patterns"]:
            if pat.search(text):
                score += weight
                hit_keywords.append(pat.pattern.strip(r'\b'))
        if score >= MIN_SCORE:
            matches.append(SubThemeMatch(
                theme=sub["theme"],
                sub_theme=sub["sub_theme"],
                score=score,
                matched_keywords=hit_keywords,
            ))
    matches.sort(key=lambda m: -m.score)
    return matches


def extract_tickers(text: str) -> list[str]:
    clean = CURRENCY_RE.sub("", text)
    tickers = TICKER_RE.findall(clean)
    return [t for t in tickers if t not in FALSE_POSITIVES]


def _get_ticker_context(ticker: str, text: str, window: int = 3) -> str:
    """
    Extract the local context around a ticker in a multi-line tweet.

    Strategy:
      - Split tweet into lines/sections on newlines
      - Find the line(s) containing the ticker
      - Return headline (line 0) + those lines + `window` surrounding lines
      - This prevents nuclear keywords on line 5 bleeding into quantum
        tickers on line 12 of the same ecosystem-list tweet
    """
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    if not lines:
        return text

    headline = lines[0]
    ticker_pat = re.compile(r'\$' + re.escape(ticker) + r'\b')
    ticker_lines = [i for i, l in enumerate(lines) if ticker_pat.search(l)]

    if not ticker_lines:
        # ticker not found by line (shouldn't happen) — fall back to full text
        return text

    # gather headline + surrounding lines
    context_indices = set([0])  # always include first line (theme header)
    for idx in ticker_lines:
        for j in range(max(0, idx - window), min(len(lines), idx + window + 1)):
            context_indices.add(j)

    return '\n'.join(lines[i] for i in sorted(context_indices))


# ── classify a corpus ─────────────────────────────────────────────────────────
def classify_tweets(tweets: list[dict], handle: str, taxonomy: dict) -> list[TweetClassification]:
    results = []
    for tw in tweets:
        text = tw["text"]
        tickers = extract_tickers(text)
        if not tickers:
            continue

        # Per-ticker proximity-aware classification
        # Each ticker gets scored on its local context, not the whole tweet
        ticker_matches: dict[str, list[SubThemeMatch]] = {}
        for ticker in tickers:
            context = _get_ticker_context(ticker, text)
            matches = score_text(context, taxonomy)
            ticker_matches[ticker] = matches

        # Tweet-level matches = union of all ticker matches (for reporting)
        all_matches = score_text(text, taxonomy)

        results.append(TweetClassification(
            tweet_id=tw["id"],
            handle=handle,
            date=tw["created_at_utc"][:10],
            text=text,
            tickers=tickers,
            matches=all_matches,
            ticker_matches=ticker_matches,
        ))
    return results


# ── aggregation: ticker → classification summary ──────────────────────────────
def aggregate_by_ticker(classifications: list[TweetClassification]) -> dict:
    """
    Returns per-ticker summary:
    {
      ticker: {
        first_seen: date,
        total_mentions: int,
        handles: {handle: count},
        theme_scores: {(theme, sub_theme): cumulative_score},
        best_theme: str,
        best_sub_theme: str,
        catalyst_tweets: [tweet_id, ...]
      }
    }
    """
    ticker_data = defaultdict(lambda: {
        "first_seen": None,
        "total_mentions": 0,
        "handles": defaultdict(int),
        "theme_scores": defaultdict(int),
        "tweet_ids": [],
    })

    for clf in classifications:
        for ticker in clf.tickers:
            td = ticker_data[ticker]
            td["total_mentions"] += 1
            td["handles"][clf.handle] += 1
            td["tweet_ids"].append(clf.tweet_id)
            if td["first_seen"] is None or clf.date < td["first_seen"]:
                td["first_seen"] = clf.date
            ticker_matches = clf.ticker_matches.get(ticker, clf.matches)
            for m in ticker_matches:
                td["theme_scores"][(m.theme, m.sub_theme)] += m.score

    # resolve best theme/sub_theme per ticker
    result = {}
    for ticker, td in ticker_data.items():
        if td["theme_scores"]:
            best = max(td["theme_scores"].items(), key=lambda x: x[1])
            best_theme, best_sub_theme = best[0]
        else:
            best_theme, best_sub_theme = "Unclassified", "Unclassified"

        all_themes = sorted(
            [{"theme": k[0], "sub_theme": k[1], "score": v}
             for k, v in td["theme_scores"].items()],
            key=lambda x: -x["score"]
        )
        result[ticker] = {
            "first_seen": td["first_seen"],
            "total_mentions": td["total_mentions"],
            "handles": dict(td["handles"]),
            "handles_count": len(td["handles"]),
            "best_theme": best_theme,
            "best_sub_theme": best_sub_theme,
            "all_themes": all_themes[:3],   # top 3 theme/sub_theme combos
            "tweet_ids": td["tweet_ids"],
        }
    return result


# ── entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    BASE = Path(__file__).parent.parent / "probes/variance"
    RUNS = {
        "speculator_io": BASE / "2026-06-06_speculator_io/twitterapi_run1.json",
        "michaelsikand":  BASE / "2026-06-06_michaelsikand/twitterapi_run1.json",
        "zephyr_z9":      BASE / "2026-06-06_zephyr_z9/twitterapi_run1.json",
        "kawzinvests":    BASE / "2026-06-12_kawzinvests/twitterapi_run1.json",
    }

    print("Loading taxonomy...")
    taxonomy = load_taxonomy(TAXONOMY_PATH)
    print(f"  {len(taxonomy)} sub_themes loaded")

    all_classifications = []
    for handle, path in RUNS.items():
        with open(path) as f:
            tweets = json.load(f)
        clfs = classify_tweets(tweets, handle, taxonomy)
        all_classifications.extend(clfs)
        classified_with_theme = sum(1 for c in clfs if c.matches)
        print(f"  {handle}: {len(tweets)} tweets → {len(clfs)} with tickers/signal, "
              f"{classified_with_theme} with theme match")

    # aggregate
    ticker_summary = aggregate_by_ticker(all_classifications)
    tickers_classified = sum(1 for v in ticker_summary.values()
                             if v["best_theme"] != "Unclassified")

    print(f"\n{len(ticker_summary)} unique tickers, "
          f"{tickers_classified} classified ({tickers_classified/len(ticker_summary):.0%})")

    # ── print results ──────────────────────────────────────────────────────────
    print(f"\n{'TICKER':<8} {'MENTIONS':>8}  {'HANDLES':>7}  {'THEME':<20}  {'SUB_THEME':<35}  FIRST_SEEN")
    print("-" * 110)

    # sort by mentions desc
    for ticker, info in sorted(ticker_summary.items(), key=lambda x: -x[1]["total_mentions"]):
        h_str = "/".join(sorted(info["handles"].keys()))
        print(f"${ticker:<7} {info['total_mentions']:>8}  {info['handles_count']:>7}  "
              f"{info['best_theme']:<20}  {info['best_sub_theme']:<35}  {info['first_seen']}")

    # ── save JSON ──────────────────────────────────────────────────────────────
    out = BASE / "ticker_classified.json"
    with open(out, "w") as f:
        json.dump(ticker_summary, f, indent=2, default=str)
    print(f"\nFull classification saved → {out}")

    # ── theme distribution ─────────────────────────────────────────────────────
    from collections import Counter
    theme_counts = Counter(v["best_theme"] for v in ticker_summary.values()
                           if v["best_theme"] != "Unclassified")
    sub_theme_counts = Counter(
        (v["best_theme"], v["best_sub_theme"]) for v in ticker_summary.values()
        if v["best_theme"] != "Unclassified"
    )
    print("\n=== THEME DISTRIBUTION ===")
    for theme, count in theme_counts.most_common():
        print(f"  {theme:<20} {count:>4} tickers")

    print("\n=== SUB_THEME DISTRIBUTION (top 20) ===")
    for (theme, sub), count in sub_theme_counts.most_common(20):
        print(f"  {theme:<20} > {sub:<35} {count:>4} tickers")
