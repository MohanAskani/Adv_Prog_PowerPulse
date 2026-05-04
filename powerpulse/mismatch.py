"""Renewable mismatch calculations.

The generation aggregate is monthly and state-level, while demand is hourly and
state-level. These helpers align both sources at state-month resolution and keep
county analysis framed as demand exposure rather than county renewable supply.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from powerpulse.stress import monthly_demand_frame


def monthly_mismatch_frame(hourly: pd.DataFrame, generation: pd.DataFrame) -> pd.DataFrame:
    """Join hourly demand aggregates with monthly generation by state."""
    demand = monthly_demand_frame(hourly)
    gen = generation.copy()
    out = demand.merge(gen, on=["year", "month", "state"], how="inner", suffixes=("", "_generation"))
    out = out.sort_values(["state", "date"]).reset_index(drop=True)

    out["renewable_gap_mwh"] = out["demand_mwh"] - out["renewable_generation_mwh"]
    out["renewable_gap_mwh"] = out["renewable_gap_mwh"].clip(lower=0)
    out["renewable_to_demand"] = out["renewable_generation_mwh"] / out["demand_mwh"].replace(0, np.nan)
    out["generation_to_demand"] = out["total_generation_mwh"] / out["demand_mwh"].replace(0, np.nan)
    out["gap_ratio"] = out["renewable_gap_mwh"] / out["demand_mwh"].replace(0, np.nan)
    out["peak_load_gw"] = out["peak_load_mw"] / 1000
    out["avg_load_gw"] = out["avg_load_mw"] / 1000

    q75 = out.groupby("state")["demand_mwh"].transform(lambda s: s.quantile(0.75))
    out["demand_period"] = np.where(out["demand_mwh"] >= q75, "High-demand month", "Other month")
    return out


def state_mismatch_summary(monthly: pd.DataFrame) -> pd.DataFrame:
    """Summarize renewable mismatch by state with a transparent 0-100 score."""
    high = monthly[monthly["demand_period"] == "High-demand month"]

    base = monthly.groupby("state", as_index=False).agg(
        avg_monthly_demand_mwh=("demand_mwh", "mean"),
        peak_monthly_demand_mwh=("demand_mwh", "max"),
        avg_peak_load_mw=("peak_load_mw", "mean"),
        avg_renewable_generation_mwh=("renewable_generation_mwh", "mean"),
        avg_renewable_share=("renewable_share", "mean"),
        avg_renewable_to_demand=("renewable_to_demand", "mean"),
        avg_gap_mwh=("renewable_gap_mwh", "mean"),
        avg_gap_ratio=("gap_ratio", "mean"),
    )
    high_summary = high.groupby("state", as_index=False).agg(
        high_month_renewable_share=("renewable_share", "mean"),
        high_month_gap_ratio=("gap_ratio", "mean"),
        high_month_gap_mwh=("renewable_gap_mwh", "mean"),
    )
    out = base.merge(high_summary, on="state", how="left")

    # Higher score means high demand coincides with larger renewable coverage gaps.
    gap_score = out["high_month_gap_ratio"].rank(pct=True) * 100
    demand_score = out["peak_monthly_demand_mwh"].rank(pct=True) * 100
    renewable_shortfall_score = (1 - out["high_month_renewable_share"].rank(pct=True)) * 100
    out["mismatch_score"] = (0.50 * gap_score) + (0.30 * renewable_shortfall_score) + (0.20 * demand_score)
    out["avg_monthly_demand_twh"] = out["avg_monthly_demand_mwh"] / 1e6
    out["peak_monthly_demand_twh"] = out["peak_monthly_demand_mwh"] / 1e6
    out["avg_gap_twh"] = out["avg_gap_mwh"] / 1e6
    out["high_month_gap_twh"] = out["high_month_gap_mwh"] / 1e6
    out["avg_peak_load_gw"] = out["avg_peak_load_mw"] / 1000
    return out.sort_values("mismatch_score", ascending=False).reset_index(drop=True)


def worst_mismatch_months(monthly: pd.DataFrame, state: str, limit: int = 12) -> pd.DataFrame:
    """Highest-gap months for one state."""
    cols = [
        "date",
        "state",
        "demand_mwh",
        "renewable_generation_mwh",
        "renewable_share",
        "renewable_to_demand",
        "renewable_gap_mwh",
        "gap_ratio",
        "peak_load_gw",
        "demand_period",
    ]
    return (
        monthly.loc[monthly["state"] == state, cols]
        .sort_values(["gap_ratio", "renewable_gap_mwh"], ascending=False)
        .head(limit)
        .reset_index(drop=True)
    )
