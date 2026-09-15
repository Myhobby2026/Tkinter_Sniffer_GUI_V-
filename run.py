"""Convenience launcher:  python run.py [--theme light] [--version]

Equivalent to ``python -m app.main`` — works from the repository root.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.main import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
