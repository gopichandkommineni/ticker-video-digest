"""Pydantic schemas handed to the model as structured-output definitions.

Kept separate from models.py because these are *versioned wire contracts*: a
change here bumps `schema_version` and creates a new generation of extraction
rows rather than editing existing ones (ADR-0007).
"""

from __future__ import annotations

SCHEMA_VERSION = 1

# The per-document and synthesis output schemas are DocumentInsights and
# CompanyProfile in career_compass.models. This module holds their serialized
# JSON-Schema form for the API call, plus any version-shim logic needed to read
# older extraction payloads.
