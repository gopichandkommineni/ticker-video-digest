import logging
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

_CONFIG_PATH = Path("config/manual_notes.yaml")


def load_manual_notes_from_yaml(path: Path = _CONFIG_PATH) -> dict[str, dict]:
    """Read config/manual_notes.yaml and return {ticker: {'catalyst': str|None, 'red_flag': str|None}}.

    Validates that all keys are uppercase ticker symbols and all values are str or None.
    Logs warnings for entries that fail validation.
    Raises FileNotFoundError if path does not exist.
    Raises ValueError for keys that are not uppercase or values of wrong type.
    """
    if not path.exists():
        raise FileNotFoundError(f"Manual notes YAML not found: {path}")

    with path.open("r") as fh:
        raw = yaml.safe_load(fh)

    if raw is None:
        return {}

    result: dict[str, dict] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or key != key.upper() or not key.isalpha():
            raise ValueError(
                f"Invalid ticker key {key!r}: must be an uppercase alphabetic string"
            )

        if not isinstance(value, dict):
            raise ValueError(
                f"Entry for {key!r} must be a mapping, got {type(value).__name__}"
            )

        catalyst = value.get("catalyst")
        red_flag = value.get("red_flag")

        if catalyst is not None and not isinstance(catalyst, str):
            raise ValueError(
                f"catalyst for {key!r} must be str or null, got {type(catalyst).__name__}"
            )
        if red_flag is not None and not isinstance(red_flag, str):
            raise ValueError(
                f"red_flag for {key!r} must be str or null, got {type(red_flag).__name__}"
            )

        result[key] = {"catalyst": catalyst, "red_flag": red_flag}

    return result
