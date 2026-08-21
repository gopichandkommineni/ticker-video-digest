"""The only LLM stage.

Two passes: per-document extraction, then cross-document synthesis per
company. Outputs are versioned and additive, never overwritten (ADR-0007), so
a prompt change is an experiment rather than a migration.
"""
