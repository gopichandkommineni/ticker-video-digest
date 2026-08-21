"""Scoring. Pure functions over the canonical store.

No network, no LLM, no clock beyond an injected `now`. Scores must move only
when data or config moves — that is what makes a trend line mean something,
and what makes this layer unit-testable against fixtures.
"""
