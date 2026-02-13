"""Shared test fixtures and configuration."""

import sys
from pathlib import Path

# Ensure the backend root is on the path so `from src.xxx` imports work
backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))
