"""Raw bytes → the common Document shape.

Pure, deterministic, offline. That constraint is what makes a parser fix
replayable across the entire raw store without re-fetching anything
(ADR-0002), and it is the reason this is a separate stage rather than part of
fetch.
"""
