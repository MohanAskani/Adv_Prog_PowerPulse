"""Value Proposition page - the Shark Tank pitch for PowerPulse.

Owner: Debuggers Team
"""

from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="Value Proposition")

st.title("PowerPulse")
st.markdown("*Why this tool exists and why it matters right now*")
st.divider()

# ── WHO IS THIS FOR ────────────────────────────────────────────────────────────
st.header("Who Is This Tool For?")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("### 🏛️ Policymakers")
    st.caption(
        "State energy commissions, public utility commissions, "
        "and legislative staff who need to justify grid investments "
        "or demand-response programs with hard data."
    )

with col2:
    st.markdown("### 📊 Energy Analysts")
    st.caption(
        "Consultants, ISOs/RTOs, and utility planners who track "
        "load patterns, seasonal peaks, and capacity requirements "
        "across 3,100+ U.S. counties."
    )

with col3:
    st.markdown("### ⚡ Grid Planners")
    st.caption(
        "Engineers and operations teams forecasting congestion, "
        "planning maintenance windows, or evaluating renewable "
        "integration scenarios."
    )

with col4:
    st.markdown("### 🎓 Students & Researchers")
    st.caption(
        "Academic teams studying energy policy, climate resilience, "
        "or the energy transition who need accessible historical "
        "load data without building a data pipeline from scratch."
    )

st.divider()

# ── WHAT PROBLEM DOES IT SOLVE ────────────────────────────────────────────────
st.header("The Problem Static Reports & Dashboards Don't Solve")

problem_col, solution_col = st.columns([1, 1.2])

with problem_col:
    st.markdown("### Pain Points")
    st.markdown(
        """
        - 📄 **Static PDF reports** are published quarterly, too slow for real-time decisions  
        - 🔒 **Proprietary tools** like utility billing portals don't let you compare states  
        - 📉 **Dashboards show what happened**, not why it happened or what's coming next  
        - 🤖 **ChatGPT can guess** but can't cite a 3,100-county, 8-year hourly dataset  
        - 🧮 **Spreadsheets break** when you try to pivot 70 million rows  
        """
    )

with solution_col:
    st.markdown("### What PowerPulse Does Differently")
    st.markdown(
        """
        |        Capability              |
        |----|
        | Filter by state, year, month, hour (Interactive) |
        | Compare multiple states side-by-side | 
        | Quantified grid stress score (0-100) |
        | Renewable mismatch index per state, per season |
        | Short-term load forecast |
        | Drill down to county level |
        | Load in under 5 seconds |
        | Simulate "what-if" scenarios with storage & demand response |
        """
    )

st.divider()

# ── WHY IT MATTERS NOW ────────────────────────────────────────────────────────
st.header("Why It Matters Now")

urgent_col1, urgent_col2, urgent_col3 = st.columns(3)

with urgent_col1:
    st.markdown("### 🌡️ Summer Peak Crises")
    st.caption(
        "2023 and 2024 set record heat waves. Texas ERCOT, California CAISO, "
        "and MISO all issued emergency alerts. PowerPulse lets you see "
        "*which hours* drove peak stress and which states are most vulnerable."
    )

with urgent_col2:
    st.markdown("### 🌪️ Extreme Weather Volatility")
    st.caption(
        "Polar vortexes, wildfires, and droughts are no longer 1-in-50-year events. "
        "Grid planners need to stress-test for scenarios that historical averages "
        "smooth over. Our volatility and ramp-severity metrics surface exactly that."
    )

with urgent_col3:
    st.markdown("### 🌱 Renewable Penetration")
    st.caption(
        "Solar and wind now represent 20%+ of generation in many states. "
        "But peak demand often hits after sundown. Our renewable mismatch "
        "module quantifies that gap, the difference no simple dashboard shows."
    )

st.markdown(
    """
    > **The grid is changing faster than any single static report can keep up with.**  
    > PowerPulse is built for decision-makers who need to ask *"what if"*, and get 
    > an answer backed by 8 years of hourly data, not a gut feeling.
    """
)

st.divider()

# ── WHAT THE USER WALKS AWAY WITH ─────────────────────────────────────────────
st.header("What You Walk Away With (In 2–3 Minutes)")

step1, step2, step3 = st.columns(3)

with step1:
    st.markdown("### 1: Orientation")
    st.markdown(
        """
        Open the app → select your state (or the nation) → see the date range. 

        Instantly know: how much load are we talking about, 
        and are we in a high-stress window right now?
        """
    )

with step2:
    st.markdown("### 2: Drill-Down")
    st.markdown(
        """
        Click into **Grid Stress** → see your state's 0–100 score. 

        Hover the chart → identify the peak hour, the volatile day, 
        the season that stresses the grid most.
        """
    )

with step3:
    st.markdown("### 3: Forward Look")
    st.markdown(
        """
        Jump to **Forecasting** → see a 7-day rolling forecast for your region. 
        
        Compare against last year's same week. You get to know whether 
        your grid is prepared for what's coming.
        """
    )

st.divider()

# ── CALL TO ACTION ─────────────────────────────────────────────────────────────
st.subheader(" Try It Now")
st.markdown(
    """
    Navigate using the sidebar to explore any of our five modules:

    | Module | What You'll Discover |
    |---|---|
    | **Demand Explorer** | Load curves by state, year, month, and hour |
    | **Grid Stress** | A transparent 0–100 stress score with contributing factors |
    | **Renewable Mismatch** | Where solar/wind don't align with peak demand |
    | **Forecasting** | 7-day rolling load predictions vs. last year |
    | **What-If Scenarios** | Simulate how demand shifts under hypothetical conditions |
    """
)

st.markdown("---")
st.caption(
    "*PowerPulse - built by Team Debuggers (Mohan Askani, Pranshu Verma, Neel Barve) "
    "for Rutgers Advanced Programming, Spring 2026.*"
)
