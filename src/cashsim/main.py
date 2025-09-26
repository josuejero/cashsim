# src/cashsim/__main__.py
"""
Executable entry-point for the 'cashsim' CLI.

This makes the pyproject script mapping
    cashsim = "cashsim.__main__:main"
work correctly, and also supports:
    python -m cashsim
"""

from .main import main as _main


def main() -> None:
    """Delegate to the real CLI implementation in cashsim.main:main()."""
    _main()


if __name__ == "__main__":
    # Supports: python -m cashsim
    main()
