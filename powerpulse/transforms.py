"""Pure-pandas transforms used by Demand Explorer and Grid Stress.

Kept deliberately framework-agnostic (no Streamlit imports) so they can be
unit-tested or reused from notebooks. Functions here take a DataFrame and
return a DataFrame -- no caching, no I/O.
"""

from __future__ import annotations

from typing import Iterable

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
