# Probes

Lightweight, offline-safe diagnostic scripts that answer specific empirical
questions about the data pipeline. Each probe type lives in its own subdirectory.
Results are committed back to this tree so they accumulate as a permanent record.

---

## variance

**Question:** Does a provider return a consistent, complete result across repeated
identical calls to the same window?

A "variable" result means the provider's search index is non-deterministic — two
back-to-back calls with the same query may return different tweet IDs or counts.
A "stable" result means repeated calls converge to the same corpus (within a small
tolerance for very recent tweets that are still propagating through the index).

See [`variance/README.md`](variance/README.md) for full documentation.

---

## gemini_digest

**Question:** Can Gemini reliably summarize ticker-bearing FinTwit tweets into a
strict-JSON `{thesis, claim, stance}` structure, and does a 30-day all-handles
run fit the free-tier request budget?

Read-only, descriptive-only probe (no buy signals, no recommendations). Cashtags
are extracted deterministically by regex; only the thesis/sector summarization
uses the LLM. Stores funnel counts, per-handle ticker concentration, a
probe-only sector map, and a thesis table.

See [`gemini_digest/README.md`](gemini_digest/README.md) for full documentation.

---

*To add a new probe type, create `probes/<type>/README.md` and append a section
here summarizing the question it answers.*
