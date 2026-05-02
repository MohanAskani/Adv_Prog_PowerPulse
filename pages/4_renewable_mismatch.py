"""Renewable Mismatch page (owner: Neel) -- stub.

This page will compare renewable generation (solar, wind, hydro) against
demand during peak vs off-peak hours, surfacing the timing gap between
when renewables produce and when the grid needs power.

Inputs needed:
  * generation by source over time (OWID dataset already in folder)
  * the same demand parquet used by Demand Explorer
  * a way to align the two (likely daily resolution to start)
"""

from __future__ import annotations

import streamlit as st


st.title("Renewable Mismatch")
st.caption(
    "How well does renewable generation align with demand at peak hours? "
    "Coming next."
)

st.info(
    "Module under construction. Will overlay renewable generation against "
    "demand and quantify the timing gap during high-stress periods."
)
