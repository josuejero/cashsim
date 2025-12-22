# CashSim API (v1)

## Run locally
~~~bash
cashsim api --reload
# or:
uvicorn cashsim.api.app:app --reload
~~~

## OpenAPI
- Swagger UI: http://127.0.0.1:8000/docs
- Schema: http://127.0.0.1:8000/openapi.json

## Example requests

### Simulate
~~~bash
curl -sS -X POST http://127.0.0.1:8000/v1/simulate \
  -H 'content-type: application/json' \
  -d @- <<'JSON'
{
  "start": "2025-01-01",
  "days": 10,
  "dials": {
    "current_cash": 300,
    "safety_cushion": 150,
    "weekday_earnings": 120,
    "gas_pct": 0.10,
    "gas_fill_size": 25,
    "bills": [{"name":"rent","amount":200,"due_day":5}],
    "oneoff_bills": [],
    "credit_cards": [],
    "ious": [],
    "interest_mode": "simple_daily_unposted"
  }
}
JSON
~~~

### Export (CSV)
~~~bash
curl -sS -X POST http://127.0.0.1:8000/v1/export \
  -H 'content-type: application/json' \
  -d @- <<'JSON'
{
  "start": "2025-01-01",
  "days": 10,
  "series_format": "csv",
  "include_events": true,
  "dials": {
    "current_cash": 300,
    "safety_cushion": 150,
    "weekday_earnings": 120,
    "gas_pct": 0.10,
    "gas_fill_size": 25,
    "bills": [{"name":"rent","amount":200,"due_day":5}],
    "oneoff_bills": [],
    "credit_cards": [],
    "ious": [],
    "interest_mode": "simple_daily_unposted"
  }
}
JSON
~~~