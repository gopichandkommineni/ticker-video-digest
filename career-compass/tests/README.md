# Tests

Mirrors the package layout. Two rules, both inherited from hard-won experience
in the sibling repo:

1. **No network in unit tests.** Ever. Adapter tests run against saved
   payloads in `tests/fixtures/raw/`, captured once via
   `career sources verify --save-fixture`. This is also why `normalize` is a
   pure function — it makes adapters trivially testable offline.

2. **The scoring layer is where the tests earn their keep.** It is pure
   arithmetic over fixtures, so it can be tested exhaustively, and it is the
   layer where a subtle bug is least likely to be noticed by eye. A demand
   score that is 15% wrong looks completely plausible.

## The invariant test

The one that matters most, from ADR-0002:

```
delete every derived table → re-run normalize + extract + analyze
                           → identical state, zero network calls
```

If that test passes, the raw/derived split is real. If it ever starts failing,
something has quietly started writing state it shouldn't.

## Layout

```
tests/
  fixtures/
    raw/            saved payloads per adapter
    profile/        a synthetic resume.yaml
    corpus/         a small hand-labelled document set
  test_taxonomy.py      duplicate slugs, ambiguous aliases
  test_normalize_*.py   one per adapter, against fixtures
  test_demand.py        decay curves, distinct-source guard
  test_supply.py        the unevidenced-rating cap especially
  test_gap.py           overrides adjust and never delete
  test_replay.py        the invariant above
```

## Testing a judgment call

`test_demand.py` and `test_supply.py` cannot assert "the score is correct" —
there is no ground truth. Assert **properties** instead:

- Demand is monotonically non-increasing as a document ages.
- Adding an evidence row never decreases supply.
- A claim with zero evidence never scores above `unevidenced_rating_cap`.
- Suppressing a gap never removes its row.
- Re-running analysis twice on identical inputs produces identical output.

Property tests over a scoring model you will keep tuning are worth far more
than assertions on specific numbers, which you would just update every time
you changed a constant.
