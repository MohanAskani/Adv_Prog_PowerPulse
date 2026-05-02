"""Grid stress scoring utilities.

The score is intentionally transparent: it ranks states by observed demand
pressure, then adds monthly generation context where source data exists.
It is not an engineering reliability metric.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


DEFAULT_WEIGHTS = {
    "peak_intensity": 30,
    "volatility": 20,
    "seasonal_extreme": 20,
    "ramp_severity": 20,
    "near_peak_persistence": 10,
}


def monthly_demand_frame(hourly: pd.DataFrame) -> pd.DataFrame:
    """State-month demand aggregates from hourly MW load."""
    monthly_mwh = hourly.resample("MS").sum()
    monthly_avg_mw = hourly.resample("MS").mean()
    monthly_peak_mw = hourly.resample("MS").max()

    out = (
        monthly_mwh.reset_index(names="date")
        .melt(id_vars="date", var_name="state", value_name="demand_mwh")
    )
    out["avg_load_mw"] = monthly_avg_mw.reset_index(drop=True).melt(value_name="avg_load_mw")["avg_load_mw"]
    out["peak_load_mw"] = monthly_peak_mw.reset_index(drop=True).melt(value_name="peak_load_mw")["peak_load_mw"]
    out["year"] = out["date"].dt.year.astype(int)
    out["month"] = out["date"].dt.month.astype(int)
    return out


def stress_component_frame(hourly: pd.DataFrame) -> pd.DataFrame:
    """Compute raw demand-stress components for each state."""
    daily_peak = hourly.resample("D").max()
    mean_load = hourly.mean()
    p99_load = hourly.quantile(0.99)
    p95_load = hourly.quantile(0.95)
    max_load = hourly.max()

    peak_intensity = p99_load / mean_load.replace(0, np.nan)
    volatility = daily_peak.std() / daily_peak.mean().replace(0, np.nan)

    summer = daily_peak[daily_peak.index.month.isin([6, 7, 8])].max()
    shoulder = daily_peak[daily_peak.index.month.isin([3, 4, 5, 9, 10, 11])].mean()
    seasonal_extreme = summer / shoulder.replace(0, np.nan)

    ramp = hourly.diff().abs()
    ramp_severity = ramp.quantile(0.95) / mean_load.replace(0, np.nan)

    near_peak_threshold = max_load * 0.90
    near_peak_persistence = hourly.ge(near_peak_threshold, axis=1).mean()

    return pd.DataFrame(
        {
            "state": hourly.columns,
            "avg_load_gw": mean_load.values / 1000,
            "p95_load_gw": p95_load.values / 1000,
            "p99_load_gw": p99_load.values / 1000,
            "peak_load_gw": max_load.values / 1000,
            "peak_intensity": peak_intensity.values,
            "volatility": volatility.values,
            "seasonal_extreme": seasonal_extreme.values,
            "ramp_severity": ramp_severity.values,
            "near_peak_persistence": near_peak_persistence.values,
        }
    )


def score_stress_components(components: pd.DataFrame, weights: dict[str, float]) -> pd.DataFrame:
    """Percentile-rank components and combine them into a 0-100 score."""
    out = components.copy()
    component_cols = list(DEFAULT_WEIGHTS)
    for col in component_cols:
        out[f"{col}_score"] = out[col].rank(pct=True) * 100

    total_weight = sum(max(float(weights.get(col, 0)), 0.0) for col in component_cols)
    if total_weight == 0:
        total_weight = 1.0

    score = sum(out[f"{col}_score"] * max(float(weights.get(col, 0)), 0.0) for col in component_cols)
    out["stress_score"] = score / total_weight
    return out.sort_values("stress_score", ascending=False).reset_index(drop=True)


def monthly_stress_context(hourly: pd.DataFrame, generation: pd.DataFrame | None = None) -> pd.DataFrame:
    """Join monthly demand with monthly generation context."""
    demand = monthly_demand_frame(hourly)
    if generation is None or generation.empty:
        return demand

    gen = generation.copy()
    out = demand.merge(gen, on=["year", "month", "state"], how="left", suffixes=("", "_generation"))
    out["demand_generation_gap_mwh"] = out["demand_mwh"] - out["total_generation_mwh"]
    out["generation_to_demand"] = out["total_generation_mwh"] / out["demand_mwh"].replace(0, np.nan)
    out["renewable_to_demand"] = out["renewable_generation_mwh"] / out["demand_mwh"].replace(0, np.nan)
    return out


def component_long_frame(scored: pd.DataFrame) -> pd.DataFrame:
    """Long-form score components for stacked/side-by-side charts."""
    score_cols = [f"{col}_score" for col in DEFAULT_WEIGHTS]
    labels = {
        "peak_intensity_score": "Peak intensity",
        "volatility_score": "Volatility",
        "seasonal_extreme_score": "Seasonal extreme",
        "ramp_severity_score": "Ramp severity",
        "near_peak_persistence_score": "Near-peak persistence",
    }
    out = scored[["state", *score_cols]].melt(id_vars="state", var_name="component", value_name="component_score")
    out["component"] = out["component"].map(labels)
    return out
