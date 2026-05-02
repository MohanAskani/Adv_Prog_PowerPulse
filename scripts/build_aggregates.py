"""
Build PowerPulse aggregate parquets from the raw county-hourly HDF5 file.

This script is meant to run **once** (and again only when source data changes).
It reads `historic_load_hourly_2016_2023_county.h5` (1.7 GB), joins the 3,109
county FIPS columns to their state, and emits compact parquet files that the
Streamlit app consumes via `powerpulse.data`.

Why pre-aggregate?
    The raw h5 is ~1.7 GB and ~218 million cells. Loading it on every
    Streamlit interaction would make the app unusable. The state-level
    aggregate is roughly 70k rows x ~50 columns -- a few MB on disk.

Usage:
    python scripts/build_aggregates.py
    python scripts/build_aggregates.py --h5 ../historic_load_hourly_2016_2023_county.h5 --out data/aggregates
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd


# Default paths assume the script is run from the powerpulse/ directory.
DEFAULT_H5 = Path("../historic_load_hourly_2016_2023_county.h5")
DEFAULT_COUNTY_LOOKUP = Path("../national_county.txt")
DEFAULT_OUT = Path("data/aggregates")


# FIPS codes that the bundled `national_county.txt` does not know about,
# but which appear in the source h5. Without these overrides the affected
# states are silently undercounted (CT) or partially missing (SD).
#
#   09110-09190: Connecticut "Planning Regions" -- the Census replaced
#                Connecticut's 8 traditional counties with 9 planning
#                regions effective 2022. Older lookup files still list
#                only the legacy county FIPS (09001-09015).
#   46102:       Oglala Lakota County, SD. Renamed from Shannon County
#                (46113) in 2015; some older lookups still have only
#                the old code.
MANUAL_FIPS_TO_STATE: dict[str, str] = {
    "09110": "CT", "09120": "CT", "09130": "CT", "09140": "CT", "09150": "CT",
    "09160": "CT", "09170": "CT", "09180": "CT", "09190": "CT",
    "46102": "SD",
}


def load_county_to_state(county_lookup_path: Path) -> dict[str, str]:
    """Map 5-digit county FIPS (e.g. '01001') to 2-letter state abbreviation.

    The Census `national_county.txt` file is comma-separated with no header:
        STATE_ABBR, STATE_FIPS, COUNTY_FIPS, COUNTY_NAME, CLASS_FP

    We construct a 5-digit FIPS by concatenating STATE_FIPS (2 digits) and
    COUNTY_FIPS (3 digits), zero-padded.
    """
    df = pd.read_csv(
        county_lookup_path,
        header=None,
        names=["state_abbr", "state_fips", "county_fips", "county_name", "class_fp"],
        dtype={"state_fips": str, "county_fips": str},
    )
    df["state_fips"] = df["state_fips"].str.zfill(2)
    df["county_fips"] = df["county_fips"].str.zfill(3)
    df["fips5"] = df["state_fips"] + df["county_fips"]
    mapping = dict(zip(df["fips5"], df["state_abbr"]))
    # Layer in manual overrides for FIPS codes the lookup file is missing.
    mapping.update(MANUAL_FIPS_TO_STATE)
    print(f"  Loaded {len(mapping):,} county->state mappings "
          f"({len(MANUAL_FIPS_TO_STATE)} manual overrides applied) "
          f"covering {len(set(mapping.values()))} states/territories")
    return mapping


def build_state_hourly(
    h5_path: Path,
    county_to_state: dict[str, str],
    out_path: Path,
) -> pd.DataFrame:
    """Read the county-hourly h5, sum demand to state level, save as parquet.

    Column convention in the h5: each county column is named like 'p01001'
    where the trailing 5 digits are the FIPS code. We strip the leading 'p'
    and look up the state. Counties absent from the lookup are dropped with
    a warning (rare; usually territories or invalid codes).

    Returns the resulting state x hour DataFrame for downstream verification.
    """
    print(f"  Reading {h5_path} (this takes ~30-60s; full file is loaded)...")
    t0 = time.time()
    df = pd.read_hdf(h5_path)
    print(f"  Loaded h5 in {time.time() - t0:.1f}s. Shape: {df.shape}, "
          f"index: {df.index.name} [{df.index.dtype}]")

    # Downcast to float32 to halve memory before the groupby.
    # MW values fit comfortably in float32 (max << 2^24).
    df = df.astype(np.float32)

    # Map column names ('p01001') -> state abbreviation ('AL').
    # Build a parallel array of state codes for groupby on the column axis.
    fips5 = [c[1:] for c in df.columns]  # strip leading 'p'
    state_codes = pd.Index(
        [county_to_state.get(f, None) for f in fips5],
        name="state",
    )

    missing = state_codes.isna().sum()
    if missing:
        print(f"  WARNING: {missing} county columns had no state mapping and "
              f"will be dropped. Sample: "
              f"{[fips5[i] for i, s in enumerate(state_codes) if s is None][:5]}")

    keep = state_codes.notna()
    df = df.loc[:, keep.tolist()]
    state_codes = state_codes[keep]

    # Group columns by state and sum. Modern pandas no longer accepts
    # groupby(axis=1) without a deprecation warning, so we transpose.
    df.columns = state_codes
    print(f"  Aggregating {df.shape[1]:,} counties -> {state_codes.nunique()} states...")
    t0 = time.time()
    state_df = df.T.groupby(level=0).sum().T
    print(f"  Aggregated in {time.time() - t0:.1f}s. "
          f"Shape: {state_df.shape}")

    # Sanity-check: totals should be positive and reasonably sized.
    national = state_df.sum(axis=1)
    print(f"  National demand sample (MW): "
          f"min={national.min():.0f}, mean={national.mean():.0f}, "
          f"max={national.max():.0f}")

    # Persist. Parquet with snappy compression is the right default.
    out_path.parent.mkdir(parents=True, exist_ok=True)
    state_df.to_parquet(out_path, compression="snappy")
    size_mb = out_path.stat().st_size / 1e6
    print(f"  Wrote {out_path} ({size_mb:.1f} MB)")

    return state_df


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--h5", type=Path, default=DEFAULT_H5,
                        help=f"Path to source HDF5 file (default: {DEFAULT_H5})")
    parser.add_argument("--county-lookup", type=Path, default=DEFAULT_COUNTY_LOOKUP,
                        help=f"Path to national_county.txt (default: {DEFAULT_COUNTY_LOOKUP})")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT,
                        help=f"Output directory for parquets (default: {DEFAULT_OUT})")
    args = parser.parse_args()

    if not args.h5.exists():
        print(f"ERROR: HDF5 not found at {args.h5}", file=sys.stderr)
        return 1
    if not args.county_lookup.exists():
        print(f"ERROR: county lookup not found at {args.county_lookup}", file=sys.stderr)
        return 1

    print("Step 1: Build county->state lookup")
    county_to_state = load_county_to_state(args.county_lookup)

    print("\nStep 2: Build state_hourly.parquet")
    build_state_hourly(args.h5, county_to_state, args.out / "state_hourly.parquet")

    print("\nDone. Future aggregates (state_daily, peak_hours, etc.) "
          "should be added as additional steps in this script.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
