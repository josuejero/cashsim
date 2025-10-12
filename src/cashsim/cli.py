from __future__ import annotations

import sys
from importlib.resources import files, as_file

def main() -> None:
    # Locate the packaged Streamlit script
    app = files("cashsim.ui").joinpath("streamlit_app.py")

    # Import Streamlit's CLI entry (new location); fall back for older versions
    try:
        from streamlit.web.cli import main as st_main  # Streamlit ≥1.10-ish
    except Exception:  # pragma: no cover
        try:
            from streamlit.cli import main as st_main  # older Streamlit
        except Exception as e:
            raise SystemExit(
                "Streamlit is required to run the UI. Install it with `pip install streamlit`."
            ) from e

    # Ensure a real filesystem path even if installed as a zip
    with as_file(app) as app_path:
        sys.argv = ["streamlit", "run", str(app_path)]
        sys.exit(st_main())
