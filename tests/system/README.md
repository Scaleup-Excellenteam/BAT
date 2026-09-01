# Universal Phase A tests

This suite compares BAT's existing online search pipeline with an independent
brute-force oracle over a bounded corpus. It covers the specification's
normalization, substring, single-edit scoring, result fields, and top-five
ordering rules.

```bash
.venv/bin/python -m pytest tests/system/test_online_completion.py
```

`adapter.py` only wires BAT's existing `DataManager -> search ->
rank_candidates` pipeline to the required API. It does not change production
behavior. Tests use a temporary isolated cache and default to BAT's one-based
line offsets; `--offset-base=0` is also supported.
