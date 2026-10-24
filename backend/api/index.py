"""Vercel entry point: serves the FastAPI app as a Python function (vercel.json routes every path here)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # so `app` imports from the backend root

from app.main import app  # noqa: E402, F401
