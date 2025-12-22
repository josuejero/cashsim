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