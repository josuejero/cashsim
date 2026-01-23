# CLI (Batch Mode)

## Install
`pip install -e ".[dev]"`

## Export a run
`cashsim export --config examples/configs/simple_baseline.json --start 2025-01-01 --days 31 --out out/simple --series-format csv`

Artifacts:
- out/simple/metrics.json
- out/simple/series.csv
- out/simple/run_meta.json

## Compare two scenarios
`cashsim compare --a examples/configs/simple_baseline.json --b examples/configs/stress_tight.json --start 2025-01-01 --days 31 --out out/compare`

Artifacts:
- out/compare/compare.json

## Data quality report
`cashsim dq report --config tests/fixtures/dq_report_config.json --out out/dq --since 2024-01-01`

Artifacts:
- `out/dq/dq_report.json` (machine-readable summary)
- `out/dq/dq_report.csv` (row per check)
- `out/dq/dq_report.md` (human-friendly markdown)
- `out/dq/issue_stub.md` (auto-generated issue stub when FAIL)

The configuration describes datasets, keys, and thresholds. Update `docs/data_dictionary.md` when the schema or allowed values change so issue stubs can link to definitions.
