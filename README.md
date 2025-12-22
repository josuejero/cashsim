# CashSim
<!--
Badges (replace links once you have them)
[![CI](https://img.shields.io/github/actions/workflow/status/<ORG>/<REPO>/ci.yml?branch=main)](<CI_URL>)
[![Coverage](https://img.shields.io/codecov/c/github/<ORG>/<REPO>)](<COVERAGE_URL>)
[![License](https://img.shields.io/github/license/<ORG>/<REPO>)](LICENSE)
[![Last Commit](https://img.shields.io/github/last-commit/<ORG>/<REPO>)](https://github.com/<ORG>/<REPO>/commits/main)
-->

[![CI](https://github.com/josuejero/cashsim/actions/workflows/ci.yml/badge.svg)](https://github.com/josuejero/cashsim/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.12+-informational.svg)](#)
[![Live App](https://img.shields.io/badge/app-live-brightgreen.svg)](https://cashsim.streamlit.app)

A modular cash(-flow) simulation + analytics sandbox designed to be **easy to run**, **easy to verify**, and **easy to extend**.
Use it to generate scenarios, stress-test assumptions, and produce reproducible outputs for analysis, reporting, or downstream ML/forecasting experiments.


---

## Why this project exists
Most “toy” simulators are either hard to reproduce or hard to extend. CashSim focuses on:
- **Reproducibility**: config-driven runs, deterministic seeds, repeatable outputs
- **Extensibility**: clear separation between simulation logic, analytics, and ML hooks
- **Auditability**: simple commands to run, test, and sanity-check results

---

## What you can do with CashSim
- Run **deterministic** or **Monte Carlo** simulations from a configuration file
- Generate **scenario outputs** (CSV/Parquet/JSON – depending on your implementation)
- Compute **summary metrics** (distributions, risk bands, sensitivities)
- Export analysis-ready artifacts for notebooks/dashboards
- Train/evaluate forecasting or risk models on simulated and/or real data

---

## For employers and reviewers
If you’re reviewing this repo for a specific role, here’s where to look first:

- **Software Engineer / Developer**: core domain logic, interfaces, tests, and code structure  
  → `src/` (or equivalent), `tests/`, `docs/architecture.md`
- **AI / ML Engineer**: training pipeline, evaluation, experiment tracking, inference entrypoints  
  → `ml/`, `pipelines/`, `models/`, `scripts/train.*`, `scripts/evaluate.*`
- **Data Scientist / Analyst**: notebooks, EDA, metrics, assumptions, and reporting  
  → `notebooks/`, `reports/`, `data_dictionary.md`
- **DevOps / Cloud Engineer**: containerization, CI, infra-as-code, observability  
  → `Dockerfile`, `docker-compose.yml`, `.github/workflows/`, `infra/`


---

## Project structure (example)
````

.
├─ src/                  # Simulation + analytics code
├─ tests/                # Unit/integration tests
├─ notebooks/            # EDA and reporting notebooks 
├─ configs/              # Reproducible run configs (YAML/JSON)
├─ data/                 # Local data (gitignored) or sample data
├─ scripts/              # CLI entrypoints (run/train/evaluate)
├─ infra/                # IaC (Terraform/CDK/etc.)
├─ docs/                 # Architecture + design notes
└─ README.md

````

---

## Quickstart

### 1) Clone
````
git clone https://github.com/josuejero/cashsim.git
cd cashsim
````

### 2) Create an environment

Pick the option that matches your stack:

**Python (venv)**

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
```

**Node**

```bash
npm install
```

**Docker**

```bash
docker build -t cashsim .
docker run --rm -it cashsim --help
```


### 3) Run a simulation

```bash
# Example CLI (adjust to match your entrypoint)
python -m cashsim run --config configs/example.yml --seed 42 --out outputs/run_001
```

---

## Usage

### Configuration

A typical run config includes:

* time horizon / step size
* starting balances
* inflows/outflows (distributions + constraints)
* scenario parameters
* random seed (for reproducibility)

Example:

```yaml
# configs/example.yml (illustrative)
horizon_months: 24
start_cash: 100000
seed: 42

inflows:
  - name: revenue
    dist: normal
    mean: 25000
    std: 5000

outflows:
  - name: payroll
    dist: fixed
    value: 18000
```

### Outputs

CashSim is designed to produce:

* a **raw time series** (per run / per path)
* a **summary report** (aggregates, percentiles, worst-case slices)
* optional artifacts for dashboards or model training

---

## Testing and quality

Run the full test suite:

```bash
# Python example
pytest -q
```

Run linting/type checks (if configured):

```bash
# Examples — adjust to your repo
ruff check .
mypy .
```

Recommended “one command” checks (if you add a Makefile):

```bash
make test
make lint
make format
make typecheck
```

---

## Reproducibility checklist

* [ ] Runs accept a `--seed` and log it
* [ ] Config files fully define a run (no hidden defaults)
* [ ] Outputs include metadata: git commit, config hash, timestamp
* [ ] Dependencies are pinned (lockfile or pinned requirements)

---

## Deployment

If you expose CashSim via an API or job runner:

* local: `docker compose up`
* production: deploy via your platform of choice (Kubernetes, ECS, Cloud Run, etc.)
* observability: structured logs + metrics + traces where appropriate

---


## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you’d like to change.

* Keep changes small and well-tested
* Update docs/config examples when behavior changes

---

## License

MIT — see **LICENSE**.


