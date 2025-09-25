from __future__ import annotations

import subprocess
import sys
import importlib.resources as ir


def main() -> None:
    # Run the bundled Streamlit app no matter where the package is installed.
    with ir.as_file(ir.files("cashsim.ui") / "streamlit_app.py") as app:
        sys.exit(subprocess.call([sys.executable, "-m", "streamlit", "run", str(app)]))


if __name__ == "__main__":
    main()
