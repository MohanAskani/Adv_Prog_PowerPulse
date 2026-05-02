"""Overview page (owner: Pranshu) -- stub.

The landing page should give a one-glance picture of the dataset and
preview the four modules. Once `state_hourly.parquet` is built it can show:
  * total counties / states covered, date range, total observations
  * national peak demand and when it occurred
  * teasers / links to each of the analysis modules
"""

from __future__ import annotations

import streamlit as st

from powerpulse.data import date_range, list_states


st.title("PowerPulse")
st.caption(
    "A web tool for exploring U.S. electricity demand, grid stress, "
    "renewable mismatch, and short-term forecasting."
)

st.markdown(
    """
    **Team Debuggers** — Mohan Askani, Pranshu Verma, Neel Barve
    *Rutgers Advanced Programming, Spring 2026 final project*

    This app extends our midterm analysis of U.S. electricity demand into
    an interactive tool. Use the sidebar to navigate between modules.
    """
)

try:
    states = list_states()
    start, end = date_range()
    col1, col2, col3 = st.columns(3)
    col1.metric("States covered", len(states))
    col2.metric("Date range start (UTC)", start.strftime("%Y-%m-%d"))
    col3.metric("Date range end (UTC)", end.strftime("%Y-%m-%d"))
except FileNotFoundError as e:
    st.warning(str(e))

st.divider()
st.subheader("Modules")
st.markdown(
    """
    - **Demand Explorer** — interactive views of demand by state, year,
      hour, and season *(Mohan)*
    - **Grid Stress** — transparent stress score per state *(Mohan)*
    - **Renewable Mismatch** — alignment of renewable generation with
      peak demand *(Neel)*
    - **Forecasting** — short-term forecasts for selected regions
      *(deferred)*
    """
)
