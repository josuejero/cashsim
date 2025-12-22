# Deploy options (no-infra / free tiers)

## Option A: Streamlit Community Cloud (UI)
Best for: quick public demo of the UI.

### Steps
1. Push the repo to GitHub.
2. Ensure your entrypoint is the Streamlit app (e.g., `src/cashsim/ui/streamlit_app.py`).
3. Add a dependency file for Community Cloud builds. A safe default for this repo is a `requirements.txt` at repo root: