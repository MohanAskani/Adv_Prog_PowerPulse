"""Build monthly state-level generation aggregate for PowerPulse.

Input:
    monthly_gen_2001_24.xlsx

Output:
    data/aggregates/generation_monthly.parquet
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


DEFAULT_INPUT = Path("../monthly_gen_2001_24.xlsx")
DEFAULT_OUTPUT = Path("data/aggregates/generation_monthly.parquet")
LEGACY_PREFIXES = ("2001", "2003", "2005", "2008", "2010")

RENEWABLE_SOURCES = {
    "Hydroelectric Conventional",
    "Solar Thermal and Photovoltaic",
    "Wind",
    "Wood and Wood Derived Fuels",
    "Other Biomass",
    "Geothermal",
}

FOSSIL_SOURCES = {"Coal", "Natural Gas", "Petroleum", "Other Gases"}


def read_generation_workbook(path: Path) -> pd.DataFrame:
    """Read EIA monthly generation workbook despite inconsistent sheet headers."""
    xl = pd.ExcelFile(path)
    frames: list[pd.DataFrame] = []

    for sheet in xl.sheet_names:
        if sheet == "EnergySource_Notes":
            continue
        header = 0 if sheet.startswith(LEGACY_PREFIXES) else 4
        df = pd.read_excel(path, sheet_name=sheet, header=header)
        df.columns = [str(c).replace("\n", " ").strip().upper() for c in df.columns]

        generation_cols = [c for c in df.columns if "GENERATION" in c]
        if not generation_cols:
            continue

        df = df.rename(
            columns={
                generation_cols[0]: "generation_mwh",
                "TYPE OF PRODUCER": "producer_type",
                "ENERGY SOURCE": "energy_source",
            }
        )
        df = df[["YEAR", "MONTH", "STATE", "producer_type", "energy_source", "generation_mwh"]]
        df = df.rename(columns={"YEAR": "year", "MONTH": "month", "STATE": "state"})
        frames.append(df)

    if not frames:
        raise ValueError(f"No generation sheets found in {path}")

    raw = pd.concat(frames, ignore_index=True)
    raw["year"] = pd.to_numeric(raw["year"], errors="coerce")
    raw["month"] = pd.to_numeric(raw["month"], errors="coerce")
    raw["generation_mwh"] = pd.to_numeric(raw["generation_mwh"], errors="coerce")
    raw = raw.dropna(subset=["year", "month", "state", "producer_type", "energy_source", "generation_mwh"])
    raw["year"] = raw["year"].astype(int)
    raw["month"] = raw["month"].astype(int)
    raw["state"] = raw["state"].astype(str).str.strip()
    raw["producer_type"] = raw["producer_type"].astype(str).str.strip()
    raw["energy_source"] = raw["energy_source"].astype(str).str.strip()
    return raw


def build_generation_monthly(raw: pd.DataFrame) -> pd.DataFrame:
    """Aggregate source rows into monthly total, renewable, and fossil columns."""
    raw = raw[
        (raw["producer_type"] == "Total Electric Power Industry")
        & (raw["state"] != "US-Total")
    ].copy()

    keys = ["year", "month", "state"]
    total = (
        raw[raw["energy_source"] == "Total"]
        .groupby(keys, as_index=False)["generation_mwh"]
        .sum()
        .rename(columns={"generation_mwh": "total_generation_mwh"})
    )
    renewable = (
        raw[raw["energy_source"].isin(RENEWABLE_SOURCES)]
        .groupby(keys, as_index=False)["generation_mwh"]
        .sum()
        .rename(columns={"generation_mwh": "renewable_generation_mwh"})
    )
    fossil = (
        raw[raw["energy_source"].isin(FOSSIL_SOURCES)]
        .groupby(keys, as_index=False)["generation_mwh"]
        .sum()
        .rename(columns={"generation_mwh": "fossil_generation_mwh"})
    )

    out = total.merge(renewable, on=keys, how="left").merge(fossil, on=keys, how="left")
    out[["renewable_generation_mwh", "fossil_generation_mwh"]] = out[
        ["renewable_generation_mwh", "fossil_generation_mwh"]
    ].fillna(0.0)
    denominator = out["total_generation_mwh"].where(out["total_generation_mwh"] != 0)
    out["renewable_share"] = out["renewable_generation_mwh"] / denominator
    out["fossil_share"] = out["fossil_generation_mwh"] / denominator
    out["date"] = pd.to_datetime(dict(year=out["year"], month=out["month"], day=1))
    return out.sort_values(["state", "year", "month"]).reset_index(drop=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    if not args.input.exists():
        raise FileNotFoundError(args.input)

    out = build_generation_monthly(read_generation_workbook(args.input))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(args.output, compression="snappy")
    print(f"Wrote {args.output} ({len(out):,} rows, {args.output.stat().st_size / 1e6:.2f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
