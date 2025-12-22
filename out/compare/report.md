# CashSim Compare Report

- start: 2025-01-01
- days: 31
- threshold: 0.01
- series_diff: series_diff.csv

## Metrics

| metric | A | B | delta |
|---|---:|---:|---:|
| accrued_interest_estimate | 0 | 16.07 | 16.07 |
| cushion_breach_date | 2025-01-01 | 2025-01-01 |  |
| first_negative_date | 2025-01-01 | 2025-01-01 |  |
| friend_ask_latest_date | 2025-01-01 | 2025-01-01 |  |
| friend_ask_needed | 298.0 | 704.0 | 406.0 |
| min_balance | -298.0 | -704.0 | -406.0 |
| min_balance_date | 2025-01-01 | 2025-01-01 |  |
| total_upcoming_bills | 1015.0 | 1106.0 | 91.0 |

## Timeline deltas

| field | A | B | delta_days |
|---|---|---|---:|
| cushion_breach_date | 2025-01-01 | 2025-01-01 | 0 |
| first_negative_date | 2025-01-01 | 2025-01-01 | 0 |
| friend_ask_latest_date | 2025-01-01 | 2025-01-01 | 0 |
| min_balance_date | 2025-01-01 | 2025-01-01 | 0 |

## Category totals

| category | A | B | delta |
|---|---:|---:|---:|
| cc_extra_paid | 0.0 | 0.0 | 0.0 |
| cc_mins_paid | 0.0 | 66.0 | 66.0 |
| debt_payments_total | 0.0 | 66.0 | 66.0 |
| income | 3720.0 | 2945.0 | -775.0 |
| interest_posted | 0.0 | 39.44 | 39.44 |
| non_debt_bills | 1015.0 | 1040.0 | 25.0 |
| oneoffs_paid | 0.0 | 0.0 | 0.0 |
| spend_total | 1015.0 | 1040.0 | 25.0 |

## Series divergence summary

| column | max_abs_delta | date | rmse | days_exceeding_threshold | first_exceeds_threshold_date |
|---|---:|---|---:|---:|---|
| accrued_interest_unposted | 37.69 | 2025-01-21 | 19.4 | 30 | 2025-01-01 |
| balance | 1466.0 | 2025-01-31 | 936.28 | 31 | 2025-01-01 |
| bill_due | 140.0 | 2025-01-18 | 29.09 | 3 | 2025-01-05 |
| earn | 25.0 | 2025-01-01 | 25.0 | 31 | 2025-01-01 |
| gas_bucket | 21.0 | 2025-01-04 | 10.34 | 30 | 2025-01-01 |
| total_cc_balance | 2200.0 | 2025-01-01 | 2178.8 | 31 | 2025-01-01 |
| total_iou_balance | 0.0 | 2025-01-01 | 0.0 | 0 | None |
