"""PowerPulse - app entry point.

Run with:
    streamlit run app.py

Pages are wired up via the modern `st.Page` / `st.navigation` API so that:
  * each module owner can edit one file without merge conflicts,
  * grouping (Explore vs. Analyze vs. Forecast) shows up in the sidebar,
  * the order is explicit instead of depending on filename prefixes.
"""

from __future__ import annotations

import streamlit as st


# Page-level config must be the first Streamlit call.
st.set_page_config(
    page_title="PowerPulse",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)


# Declare pages. Each path is relative to this file.
pages = {
    "Explore": [
        st.Page("pages/1_overview.py", title="Overview", default=True),
        st.Page("pages/2_demand_explorer.py", title="Demand Explorer"),
    ],
    "Analyze": [
        st.Page("pages/3_grid_stress.py", title="Grid Stress"),
        st.Page("pages/4_renewable_mismatch.py", title="Renewable Mismatch"),
    ],
    "Forecast": [
        st.Page("pages/5_forecasting.py", title="Forecasting"),
    ],
}

nav = st.navigation(pages)
nav.run()
