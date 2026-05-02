"""Pure-pandas transforms used by Demand Explorer and Grid Stress.

Kept deliberately framework-agnostic (no Streamlit imports) so they can be
unit-tested or reused from notebooks. Functions here take a DataFrame and
return a DataFrame -- no caching, no I/O.
"""

from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd


def filter_states_years(
    df: pd.DataFrame,
    states: Iterable[str] | None = None,
    years: Iterable[int] | None = None,
) -> pd.DataFrame:
    """Slice the state-hourly DataFrame to selected states and years.

    `states=None` keeps all states; `years=None` keeps all years.
    """
    out = df
    if states is not None:
        states = list(states)
        # Preserve column order from caller for reproducible plots
        keep = [s for s in states if s in out.columns]
        out = out[keep]
    if years is not None:
        years = set(int(y) for y in years)
        out = out[out.index.year.isin(years)]
    return out


def hour_of_day_average(
    df: pd.DataFrame,
    aggregator: str = "sum",
) -> pd.Series:
    """Average demand by UTC hour-of-day, summed across the given states.

    `aggregator='sum'` totals demand across the selected states first
    (the natural framing for 'aggregate U.S./regional load by hour').
    `aggregator='mean'` averages across states (useful when comparing
    a single state to a regional baseline).
    """
    if aggregator == "sum":
        series = df.sum(axis=1)
    elif aggregator == "mean":
        series = df.mean(axis=1)
    else:
        raise ValueError(f"Unknown aggregator: {aggregator!r}")
    out = series.groupby(series.index.hour).mean()
    out.index.name = "hour_utc"
    out.name = "avg_demand_mw"
    return out


def hour_of_day_per_state(df: pd.DataFrame) -> pd.DataFrame:
    """Average demand by UTC hour-of-day, one column per state.

    Used when the user wants to overlay multiple states on the same chart.
    """
    out = df.groupby(df.index.hour).mean()
    out.index.name = "hour_utc"
    return out


def aggregate_total_series(df: pd.DataFrame) -> pd.Series:
    """Aggregate state load to a single hourly series in MW."""
    series = df.sum(axis=1)
    series.name = "aggregate_mw"
    return series


def yearly_energy_twh(df: pd.DataFrame) -> pd.Series:
    """Annual electricity consumption in TWh.

    Hourly MW values are summed to MWh and then converted to TWh.
    """
    series = aggregate_total_series(df)
    out = series.groupby(series.index.year).sum() / 1e6
    out.index.name = "year"
    out.name = "energy_twh"
    return out


def yearly_energy_by_state(df: pd.DataFrame) -> pd.DataFrame:
    """Annual electricity demand in TWh, split by state."""
    out = df.groupby(df.index.year).sum() / 1e6
    out.index.name = "year"
    out = out.reset_index().melt(id_vars="year", var_name="state", value_name="energy_twh")
    return out


def yearly_boxplot_by_state(df: pd.DataFrame) -> pd.DataFrame:
    """Long-form hourly demand frame in GW, split by state."""
    frame = (df / 1e3).melt(ignore_index=False, var_name="state", value_name="demand_gw").reset_index(names="timestamp")
    frame["year"] = frame["timestamp"].dt.year.astype(int)
    return frame


def yearly_boxplot_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Long-form frame for yearly demand distributions in GW."""
    series = aggregate_total_series(df) / 1e3
    out = pd.DataFrame({
        "year": series.index.year.astype(int),
        "demand_gw": series.to_numpy(),
    })
    return out


def weekday_weekend_hourly(df: pd.DataFrame) -> pd.DataFrame:
    """Average demand by hour for weekday vs weekend."""
    series = aggregate_total_series(df) / 1e3
    frame = pd.DataFrame({
        "hour_utc": series.index.hour,
        "day_type": np.where(series.index.dayofweek < 5, "Weekday", "Weekend"),
        "demand_gw": series.to_numpy(),
    })
    out = frame.groupby(["day_type", "hour_utc"], as_index=False)["demand_gw"].mean()
    return out


def weekday_weekend_by_state(df: pd.DataFrame) -> pd.DataFrame:
    """Average demand by hour for weekday vs weekend, split by state."""
    frame = (df / 1e3).melt(ignore_index=False, var_name="state", value_name="demand_gw").reset_index(names="timestamp")
    frame["hour_utc"] = frame["timestamp"].dt.hour.astype(int)
    frame["day_type"] = np.where(frame["timestamp"].dt.dayofweek < 5, "Weekday", "Weekend")
    out = frame.groupby(["state", "day_type", "hour_utc"], as_index=False)["demand_gw"].mean()
    return out


def monthly_average_gw(df: pd.DataFrame) -> pd.Series:
    """Average aggregate demand by calendar month in GW."""
    series = aggregate_total_series(df) / 1e3
    out = series.groupby(series.index.month).mean()
    out.index.name = "month"
    out.name = "avg_demand_gw"
    return out


def monthly_average_by_state(df: pd.DataFrame) -> pd.DataFrame:
    """Average demand by calendar month in GW, split by state."""
    out = (df / 1e3).groupby(df.index.month).mean()
    out.index.name = "month"
    out = out.reset_index().melt(id_vars="month", var_name="state", value_name="avg_demand_gw")
    return out


def seasonal_average_gw(df: pd.DataFrame) -> pd.Series:
    """Average aggregate demand by meteorological season in GW."""
    series = aggregate_total_series(df) / 1e3

    def season_for_month(month: int) -> str:
        if month in (12, 1, 2):
            return "Winter"
        if month in (3, 4, 5):
            return "Spring"
        if month in (6, 7, 8):
            return "Summer"
        return "Fall"

    frame = pd.DataFrame({
        "season": [season_for_month(month) for month in series.index.month],
        "demand_gw": series.to_numpy(),
    })
    out = frame.groupby("season")["demand_gw"].mean()
    out = out.reindex(["Winter", "Spring", "Summer", "Fall"])
    out.name = "avg_demand_gw"
    return out


def seasonal_average_by_state(df: pd.DataFrame) -> pd.DataFrame:
    """Average demand by season in GW, split by state."""
    def season_for_month(month: int) -> str:
        if month in (12, 1, 2):
            return "Winter"
        if month in (3, 4, 5):
            return "Spring"
        if month in (6, 7, 8):
            return "Summer"
        return "Fall"

    frame = (df / 1e3).melt(ignore_index=False, var_name="state", value_name="demand_gw").reset_index(names="timestamp")
    frame["season"] = [season_for_month(month) for month in frame["timestamp"].dt.month]
    out = frame.groupby(["season", "state"], as_index=False)["demand_gw"].mean()
    out["season"] = pd.Categorical(out["season"], categories=["Winter", "Spring", "Summer", "Fall"], ordered=True)
    return out


def month_hour_heatmap(df: pd.DataFrame) -> pd.DataFrame:
    """Pivot table of average demand by month and hour in GW."""
    series = aggregate_total_series(df) / 1e3
    frame = pd.DataFrame({
        "month": series.index.month,
        "hour": series.index.hour,
        "demand_gw": series.to_numpy(),
    })
    out = frame.pivot_table(index="month", columns="hour", values="demand_gw", aggfunc="mean")
    out = out.reindex(index=range(1, 13), columns=range(24))
    return out


def monthly_boxplot_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Long-form frame for month-wise demand distributions in GW."""
    series = aggregate_total_series(df) / 1e3
    month_names = {
        1: "Jan",
        2: "Feb",
        3: "Mar",
        4: "Apr",
        5: "May",
        6: "Jun",
        7: "Jul",
        8: "Aug",
        9: "Sep",
        10: "Oct",
        11: "Nov",
        12: "Dec",
    }
    frame = pd.DataFrame({
        "month": series.index.month.astype(int),
        "month_name": [month_names[m] for m in series.index.month],
        "demand_gw": series.to_numpy(),
    })
    frame["month_name"] = pd.Categorical(
        frame["month_name"],
        categories=[month_names[m] for m in range(1, 13)],
        ordered=True,
    )
    return frame


def annual_volatility_gw(df: pd.DataFrame) -> pd.Series:
    """Standard deviation of hourly aggregate demand by year, in GW."""
    series = aggregate_total_series(df) / 1e3
    out = series.groupby(series.index.year).std()
    out.index.name = "year"
    out.name = "volatility_gw"
    return out


def annual_volatility_by_state(df: pd.DataFrame) -> pd.DataFrame:
    """Standard deviation of hourly demand by year, split by state."""
    out = (df / 1e3).groupby(df.index.year).std()
    out.index.name = "year"
    out = out.reset_index().melt(id_vars="year", var_name="state", value_name="volatility_gw")
    return out


def annual_peak_gw(df: pd.DataFrame) -> pd.Series:
    """Annual peak hourly aggregate demand, in GW."""
    series = aggregate_total_series(df) / 1e3
    out = series.groupby(series.index.year).max()
    out.index.name = "year"
    out.name = "peak_gw"
    return out


def annual_peak_by_state(df: pd.DataFrame) -> pd.DataFrame:
    """Annual peak hourly demand in GW, split by state."""
    out = (df / 1e3).groupby(df.index.year).max()
    out.index.name = "year"
    out = out.reset_index().melt(id_vars="year", var_name="state", value_name="peak_gw")
    return out


def extreme_hours_frame(df: pd.DataFrame, quantile: float = 0.99) -> tuple[pd.DataFrame, float]:
    """Return the extreme-load hours and the threshold used, both in GW."""
    series = aggregate_total_series(df) / 1e3
    threshold = float(series.quantile(quantile))
    frame = pd.DataFrame({
        "timestamp": series.index,
        "year": series.index.year.astype(int),
        "month": series.index.month.astype(int),
        "hour": series.index.hour.astype(int),
        "demand_gw": series.to_numpy(),
    })
    out = frame[frame["demand_gw"] >= threshold].copy()
    return out, threshold


def country_comparison_frame(df: pd.DataFrame, start_year: int = 2016, end_year: int = 2023) -> pd.DataFrame:
    """Prepare OWID country data for the cross-country comparison section."""
    out = df[(df["year"] >= start_year) & (df["year"] <= end_year)].copy()
    out["gdp_per_capita_usd"] = out["gdp"] / out["population"]
    out["electricity_per_capita_kwh"] = (out["electricity_demand"] * 1_000_000) / out["population"]
    out["electricity_demand_twh"] = out["electricity_demand"]
    return out
