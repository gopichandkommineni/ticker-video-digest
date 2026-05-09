"""Allow ``python -m ticker_digest`` to invoke the CLI."""
from ticker_digest.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
