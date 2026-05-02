"""Demand Explorer page (owner: Mohan).

First-cut of the Demand Explorer: average demand by hour of day (UTC),
filtered by state(s) and year(s). This is the page's foundational view --
follow-on iterations should add weekday-vs-weekend, monthly/seasonal,
yearly trend, and per-capita comparisons (all of which were in Mohan's
midterm notebook and need to be migrated from matplotlib to Plotly).

Notes
-----
* The chart is plotted in **UTC** because the source h5 is UTC-indexed
  and per-state local-time conversion is non-trivial (some states span
  multiple time zones). Local-time view is on the backlog.
* Demand values are summed across selected states first, then averaged
  across days. That matches the framing 'what does aggregate load look
  like for this region across the day?'.
"""

from __future__ import annotations

import streamlit as st

from powerpulse.data import get_state_hourly, list_states, date_range
from powerpulse.transforms import (
    filter_states_years,
    hour_of_day_average,
    hour_of_day_per_state,
)
from powerpulse.viz import hour_of_day_total, hour_of_day_by_state


st.title("Demand Explorer")
st.caption(
    "Interactive views of U.S. electricity demand by state, year, and hour. "
    "Source: county-hourly demand 2016–2023, aggregated to state level."
)

# ---------------------------------------------------------------------------
# Data load (cached)
# ---------------------------------------------------------------------------
try:
    df = get_state_hourly()
except FileNotFoundError as e:
    st.error(str(e))
    st.stop()

all_states = list_states()
start, end = date_range()
all_years = list(range(start.year, end.year + 1))

# ---------------------------------------------------------------------------
# Sidebar controls
# ---------------------------------------------------------------------------
with st.sidebar:
    st.subheader("Filters")
    # Default to a small comparison set so the chart isn't dominated by
    # one giant state on first load. CA, TX, NY are demand heavyweights;
    # the user can widen via the multiselect.
    selected_states = st.multiselect(
        "States",
        options=all_states,
        default=["CA", "TX", "NY"],
        help="Pick one or more states. Empty = all states (national view).",
    )
    selected_years = st.multiselect(
        "Years",
        options=all_years,
        default=all_years,
        help="Filter the date range used to compute the hour-of-day average.",
    )
    view_mode = st.radio(
        "View",
        options=["Aggregate (sum across states)", "Per state (one line each)"],
        index=0,
        help=(
            "Aggregate sums demand across selected states, then averages by hour. "
            "Per state plots one line per state (each as its own absolute demand)."
        ),
    )

# ---------------------------------------------------------------------------
# Slice + plot
# ---------------------------------------------------------------------------
states_for_query = selected_states or all_states
sliced = filter_states_years(df, states=states_for_query, years=selected_years or all_years)

if sliced.empty:
    st.warning("No rows match the current filter. Widen the year selection.")
    st.stop()

if view_mode.startswith("Aggregate"):
    series = hour_of_day_average(sliced, aggregator="sum")
    label = "all states" if not selected_states else ", ".join(selected_states)
    fig = hour_of_day_total(
        series,
        title=f"Average demand by hour of day — {label}",
    )
else:
    by_state = hour_of_day_per_state(sliced)
    fig = hour_of_day_by_state(
        by_state,
        title="Average demand by hour of day, per state",
    )

st.plotly_chart(fig, width="stretch")

# ---------------------------------------------------------------------------
# Quick summary numbers — first taste of "So What" framing for the report
# ---------------------------------------------------------------------------
agg = hour_of_day_average(sliced, aggregator="sum")
peak_hour = int(agg.idxmax())
trough_hour = int(agg.idxmin())
peak_gw = agg.max() / 1e3
trough_gw = agg.min() / 1e3
swing_pct = 100 * (peak_gw - trough_gw) / trough_gw

c1, c2, c3 = st.columns(3)
c1.metric("Peak hour (UTC)", f"{peak_hour:02d}:00", f"{peak_gw:.1f} GW")
c2.metric("Trough hour (UTC)", f"{trough_hour:02d}:00", f"{trough_gw:.1f} GW")
c3.metric("Peak vs trough", f"{swing_pct:.0f}%", help="Percent above the trough")

with st.expander("What this view is and isn't"):
    st.markdown(
        """
        - The x-axis is **UTC hour-of-day**, not local time. That means
          'hour 22' represents the same instant for every state, but
          maps to different local clock times (e.g. 6 PM Eastern, 3 PM
          Pacific). Local-time view is on the backlog.
        - 'Average' means the mean across all selected days for that
          UTC hour — it does **not** show day-to-day variation. That
          comes in the Grid Stress module.
        - Aggregate view sums state-level MW first, then averages.
          Numerically equivalent to averaging the national series.
        """
    )
