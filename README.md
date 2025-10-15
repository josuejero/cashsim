
# CashSim

> Streamlit-powered cash-flow & debt planning simulator with daily scheduling, ADB interest, and “what-if” analytics.

[![CI](https://github.com/josuejero/cashsim/actions/workflows/ci.yml/badge.svg)](https://github.com/josuejero/cashsim/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.12+-informational.svg)](#)
[![Live App](https://img.shields.io/badge/app-live-brightgreen.svg)](https://cashsim.streamlit.app)



## ✨ Features
- **Single-page Streamlit UI**: inputs, simulation, analytics, planner, wishlist (Google Sheets).
- **ADB interest math** (Decimal-correct) & due-date postings.
- **Daily planner**: variable schedule with blackout days and 7-day reserve logic.
- **Break-even grid & monthly snapshot** analytics.
- **Google Sheets** wishlist integration via service account.

## 🚀 Quickstart (local)
````bash
# 1) Python 3.12+ recommended
python -m venv .venv && source .venv/bin/activate

# 2) Install the package (editable ok)
pip install -e ".[dev]"     # or: pip install -r requirements.txt

# 3) (Optional) Google Sheets secrets for wishlist tab
#    Put TOML at: .streamlit/secrets.toml (see docs/SECRETS.md)

# 4) Launch the app
cashsim               # invokes Streamlit runner under the hood
# or: streamlit run src/cashsim/ui/streamlit_app.py
`````

## 🔧 Configuration

* Example config: [`examples/configs/sample.json`](examples/configs/sample.json)
* Local secrets: see [`docs/SECRETS.md`](docs/SECRETS.md)
  **Never commit secrets.** Use Streamlit Cloud’s Secrets for production.

## 🧪 Tests

```bash
pytest -q
```

## 📦 Deploy

### Streamlit Community Cloud (recommended)

* Connect repo → set **App file**: `src/cashsim/ui/streamlit_app.py`.
* Add **Secrets** (paste TOML from `docs/SECRETS.md` template).
* Optional: set custom subdomain (e.g., `cashsim.streamlit.app`).

### Hugging Face Spaces (Docker)

* Create Space (Docker) → add the `Dockerfile` from this repo.
* Add secrets in Space settings; write them to `.streamlit/secrets.toml` at container start.

### Google Cloud Run

* Build & push container image → **Deploy** to Cloud Run.
* Mount a Secret Manager secret to `/.streamlit/secrets.toml`.

## 🗺️ Roadmap

* CSV import/export
* Scenario comparison view
* CLI subcommands for headless batch simulation

## 🤝 Contributing

Bug reports & PRs welcome. See **CONTRIBUTING.md**.

## 📝 License

MIT — see **LICENSE**.
