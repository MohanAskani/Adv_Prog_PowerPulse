"""Cached data loaders for the PowerPulse Streamlit app.

All page-facing data access goes through this module so caching, paths, and
schema assumptions live in exactly one place. Pages should never call
`pd.read_parquet` directly -- they should call one of the helpers here.

Caching strategy:
    `st.cache_data` memoizes the return value across reruns. We pass the
    file's mtime as a cache key so re-running the ETL invalidates the cache
    automatically. If Streamlit isn't installed (e.g. during unit-style
    sanity checks), we fall back to an identity decorator so the helpers
    still work outside the app.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import pandas as pd

# Resolve repo root from this file's location: powerpulse/powerpulse/data.py
# parents[1] = powerpulse/ (the project root, containing app.py)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
AGGREGATES_DIR = PROJECT_ROOT / "data" / "aggregates"
STATE_HOURLY_PARQUET = AGGREGATES_DIR / "state_hourly.parquet"


# Make the module importable without Streamlit (useful for tests / scripts).
def _passthrough_cache(*args, **kwargs):
    """Identity decorator used when streamlit isn't available."""
    if args and callable(args[0]):
        return args[0]
    def deco(fn: Callable) -> Callable:
        return fn
    return deco


try:
    import streamlit as st
    _cache_data = st.cache_data
except ImportError:  # pragma: no cover - only hit outside the app
    _cache_data = _passthrough_cache


def _file_mtime(path: Path) -> float:
    """Used as a cache key so a re-baked parquet busts the cache."""
    return path.stat().st_mtime if path.exists() else 0.0


@_cache_data(show_spinner="Loading state-hourly demand...")
def load_state_hourly(_mtime: float | None = None) -> pd.DataFrame:
    """Hourly demand (MW) by state, indexed by UTC timestamp.

    Returns a DataFrame of shape (~70128, 49) with UTC DatetimeIndex and
    one column per state abbreviation (e.g. 'CA', 'TX'). Built by
    `scripts/build_aggregates.py` from the source HDF5.
    """
    if not STATE_HOURLY_PARQUET.exists():
        raise FileNotFoundError(
            f"Aggregate parquet not found at {STATE_HOURLY_PARQUET}.\n"
            f"Run: python scripts/build_aggregates.py  (from the powerpulse/ folder)"
        )
    return pd.read_parquet(STATE_HOURLY_PARQUET)


def get_state_hourly() -> pd.DataFrame:
    """Public convenience wrapper that passes the current mtime as cache key."""
    return load_state_hourly(_file_mtime(STATE_HOURLY_PARQUET))


@_cache_data
def list_states() -> list[str]:
    """Sorted list of state abbreviations available in the demand parquet."""
    return sorted(get_state_hourly().columns.tolist())


@_cache_data
def date_range() -> tuple[pd.Timestamp, pd.Timestamp]:
    """Min/max UTC timestamp covered by the demand data."""
    idx = get_state_hourly().index
    return idx.min(), idx.max()
