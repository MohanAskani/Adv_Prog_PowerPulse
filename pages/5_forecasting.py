"""Forecasting page -- deferred.

The proposal explicitly gates this module: ship only if a simple
time-series model beats a naive seasonal baseline. Given the May 9
deadline and the focus on demand + stress + mismatch, this is on hold.

If revived, plan:
  * forecast daily peak demand for: National, Texas (ERCOT), California
  * baseline = seasonal naive (this DOY of last year) and rolling mean
  * candidate model = SARIMA via statsmodels
  * report MAPE on a held-out 2023 test split for each region
"""

from __future__ import annotations

import streamlit as st


st.title("Forecasting")
st.caption("Held — see proposal section 5D for scope.")

st.warning(
    "Forecasting module is deferred. The proposal commits to including it "
    "only if it outperforms a naive seasonal baseline; with the May 9 "
    "deadline we are prioritising the Demand, Grid Stress, and Renewable "
    "Mismatch modules first."
)
