"""Grid Stress page (owner: Mohan) -- stub.

This page will host the transparent grid-stress score:
  * peak demand magnitude (e.g. top 1% hours per state)
  * demand volatility (std of daily peaks)
  * seasonal extreme ratio (summer max / winter min)
  * composite score with explicit, user-tunable weights

Build order suggestion:
  1. Add scripts/build_aggregates.py outputs: state_daily.parquet
     (daily peak / mean / min per state).
  2. Implement scoring functions in powerpulse/stress.py.
  3. Render here as a sortable table + bar chart, with a sidebar slider
     so the user can re-weight components and see the ranking shift.
"""

from __future__ import annotations

import streamlit as st


st.title("Grid Stress")
st.caption("Transparent stress score per state. Coming next.")

st.info(
    "Module under construction. Will combine peak demand, demand volatility, "
    "and seasonal extremes into an interpretable composite score with "
    "user-tunable weights. See pages/3_grid_stress.py for the build plan."
)
