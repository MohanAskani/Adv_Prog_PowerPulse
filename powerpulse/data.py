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

import json
from pathlib import Path
from typing import Any, Callable

import pandas as pd

# Resolve repo root from this file's location: powerpulse/powerpulse/data.py
# parents[1] = powerpulse/ (the project root, containing app.py)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = PROJECT_ROOT.parent
AGGREGATES_DIR = PROJECT_ROOT / "data" / "aggregates"
EXTERNAL_DATA_DIR = PROJECT_ROOT / "data" / "external"

STATE_HOURLY_PARQUET = AGGREGATES_DIR / "state_hourly.parquet"
COUNTY_SUMMARY_PARQUET = AGGREGATES_DIR / "county_summary.parquet"
STATE_SUMMARY_PARQUET = AGGREGATES_DIR / "state_summary.parquet"
GENERATION_MONTHLY_PARQUET = AGGREGATES_DIR / "generation_monthly.parquet"

COUNTRY_ENERGY_CSV = DATA_ROOT / "owid-energy-datav2.csv"
COUNTIES_GEOJSON = DATA_ROOT / "counties.geojson"


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


def _missing_file_message(path: Path, hint: str) -> str:
    return f"File not found at {path}\n{hint}"


def _resolve_source_file(filename: str) -> Path:
    """Look for shared data in committed app data first, then local fallbacks."""
    for candidate in (EXTERNAL_DATA_DIR / filename, PROJECT_ROOT / filename, DATA_ROOT / filename):
        if candidate.exists():
            return candidate
    return EXTERNAL_DATA_DIR / filename


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


@_cache_data(show_spinner="Loading county summary...")
def load_county_summary(_mtime: float | None = None) -> pd.DataFrame:
    """County-level average demand and per-capita metrics.

    Built by `scripts/build_aggregates.py` from the source HDF5 and county
    population workbook. Each row represents one county.
    """
    if not COUNTY_SUMMARY_PARQUET.exists():
        raise FileNotFoundError(
            _missing_file_message(
                COUNTY_SUMMARY_PARQUET,
                "Run: python scripts/build_aggregates.py",
            )
        )
    return pd.read_parquet(COUNTY_SUMMARY_PARQUET)


def get_county_summary() -> pd.DataFrame:
    """Cached county summary with a cache key tied to the parquet mtime."""
    return load_county_summary(_file_mtime(COUNTY_SUMMARY_PARQUET))


@_cache_data(show_spinner="Loading state summary...")
def load_state_summary(_mtime: float | None = None) -> pd.DataFrame:
    """State-level average demand and per-capita metrics.

    Built by `scripts/build_aggregates.py` by rolling county-level averages
    up to state totals.
    """
    if not STATE_SUMMARY_PARQUET.exists():
        raise FileNotFoundError(
            _missing_file_message(
                STATE_SUMMARY_PARQUET,
                "Run: python scripts/build_aggregates.py",
            )
        )
    return pd.read_parquet(STATE_SUMMARY_PARQUET)


def get_state_summary() -> pd.DataFrame:
    """Cached state summary with a cache key tied to the parquet mtime."""
    return load_state_summary(_file_mtime(STATE_SUMMARY_PARQUET))


@_cache_data(show_spinner="Loading monthly generation...")
def load_generation_monthly(_mtime: float | None = None) -> pd.DataFrame:
    """Monthly state-level generation by total, renewable, and fossil buckets."""
    if not GENERATION_MONTHLY_PARQUET.exists():
        raise FileNotFoundError(
            _missing_file_message(
                GENERATION_MONTHLY_PARQUET,
                "Build data/aggregates/generation_monthly.parquet from monthly_gen_2001_24.xlsx.",
            )
        )
    return pd.read_parquet(GENERATION_MONTHLY_PARQUET)


def get_generation_monthly() -> pd.DataFrame:
    """Cached monthly generation aggregate with a cache key tied to mtime."""
    return load_generation_monthly(_file_mtime(GENERATION_MONTHLY_PARQUET))


@_cache_data(show_spinner="Loading country energy data...")
def load_country_energy(_mtime: float | None = None) -> pd.DataFrame:
    """OWID country-level electricity and GDP data used for comparison views."""
    country_path = _resolve_source_file(COUNTRY_ENERGY_CSV.name)
    if not country_path.exists():
        raise FileNotFoundError(
            _missing_file_message(
                country_path,
                "Place owid-energy-datav2.csv under data/external/ or one directory above the repo root.",
            )
        )
    return pd.read_csv(country_path)


def get_country_energy() -> pd.DataFrame:
    """Cached country comparison dataset with a cache key tied to mtime."""
    return load_country_energy(_file_mtime(_resolve_source_file(COUNTRY_ENERGY_CSV.name)))


@_cache_data(show_spinner="Loading county geojson...")
def load_counties_geojson(_mtime: float | None = None) -> dict[str, Any]:
    """County GeoJSON used for choropleth maps.

    The file is intentionally kept outside the repo because it is shared
    course data rather than app code.
    """
    geojson_path = _resolve_source_file(COUNTIES_GEOJSON.name)
    if not geojson_path.exists():
        raise FileNotFoundError(
            _missing_file_message(
                geojson_path,
                "Place counties.geojson under data/external/ or one directory above the repo root.",
            )
        )
    return json.loads(geojson_path.read_text())


def get_counties_geojson() -> dict[str, Any]:
    """Cached GeoJSON with a cache key tied to the file mtime."""
    return load_counties_geojson(_file_mtime(_resolve_source_file(COUNTIES_GEOJSON.name)))


@_cache_data
def list_states() -> list[str]:
    """Sorted list of state abbreviations available in the demand parquet."""
    return sorted(get_state_hourly().columns.tolist())


@_cache_data
def date_range() -> tuple[pd.Timestamp, pd.Timestamp]:
    """Min/max UTC timestamp covered by the demand data."""
    idx = get_state_hourly().index
    return idx.min(), idx.max()
