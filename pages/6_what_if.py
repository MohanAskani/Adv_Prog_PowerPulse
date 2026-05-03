"""What‑If simulator: storage and demand response mitigations.

Provides a simple, fast counterfactual engine that applies DR and battery
dispatch per-day to shave peaks and reduce stress hours. The model is
deterministic and intended for interactive exploration, not powerflow
validation.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from powerpulse.data import get_state_hourly, list_states, date_range
from powerpulse.transforms import filter_states_years


st.markdown(
    """
    <style>
    .block-container { padding-top: 1.1rem; padding-bottom: 2rem; }
    .section-tag { font-size: .72rem; font-weight: 800; letter-spacing: .16em; text-transform: uppercase; color: #0f766e; margin-bottom: .1rem; }
    .section-title { font-size: 1.35rem; font-weight: 800; color: #0f172a; margin-bottom: .15rem; }
    .section-note { color: #64748b; font-size: .95rem; margin-bottom: .55rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


def section_header(title: str, note: str) -> None:
    st.markdown(f"<div class='section-tag'>What‑If</div><div class='section-title'>{title}</div><div class='section-note'>{note}</div>", unsafe_allow_html=True)


def simulate_counterfactual(
    series_mw: pd.Series,
    storage_power_mw: float,
    storage_hours: float,
    dr_power_mw: float,
    dr_hours_per_day: int,
) -> tuple[pd.Series, pd.DataFrame]:
    """Apply a per-day greedy DR + storage dispatch and return modified series and dispatch frame.

    - DR: applied to the top `dr_hours_per_day` hours each day, reducing demand by up to `dr_power_mw`.
    - Storage: daily energy budget = storage_power_mw * storage_hours (MWh). For each day, discharge greedily
      into the highest-demand hours up to `storage_power_mw` and remaining energy.
    """
    df = series_mw.copy().to_frame(name="demand_mw")
    df["date"] = df.index.normalize()

    dispatch_records = []

    energy_capacity_mwh = storage_power_mw * storage_hours

    out = df["demand_mw"].copy()

    for date, group in df.groupby("date"):
        hours = group.index
        demands = group["demand_mw"].copy()

        # Apply DR to top hours per day
        if dr_power_mw > 0 and dr_hours_per_day > 0:
            top_hours = demands.nlargest(dr_hours_per_day).index
            for h in top_hours:
                red = min(dr_power_mw, out.loc[h])
                out.loc[h] = out.loc[h] - red
                dispatch_records.append({"timestamp": h, "type": "dr", "mw": red})

        # Storage: energy budget per day (MWh)
        energy_left_mwh = energy_capacity_mwh

        # iterate hours by demand descending to shave peaks
        for h in demands.sort_values(ascending=False).index:
            if energy_left_mwh <= 0 or storage_power_mw <= 0:
                break
            avail = min(storage_power_mw, out.loc[h])  # MW that can be discharged this hour
            # energy consumed if we discharge at avail for one hour
            use_mwh = min(avail, energy_left_mwh)
            use_mw = use_mwh  # since 1 hour steps, MWh ~ MW
            out.loc[h] = out.loc[h] - use_mw
            energy_left_mwh -= use_mwh
            if use_mw > 0:
                dispatch_records.append({"timestamp": h, "type": "storage", "mw": use_mw})

    dispatch = pd.DataFrame(dispatch_records)
    if not dispatch.empty:
        dispatch = dispatch.set_index("timestamp").sort_index()
    else:
        dispatch = pd.DataFrame(columns=["type", "mw"])  # empty frame

    return out, dispatch


def common_layout(fig: go.Figure, title: str, y_title: str, x_title: str, height: int = 420) -> go.Figure:
    fig.update_layout(template="plotly_white", title=title, yaxis_title=y_title, xaxis_title=x_title, height=height, margin=dict(l=40, r=20, t=64, b=44), hovermode="x unified")
    return fig


def main():
    section_header("What‑If: storage & DR","Estimate how simple mitigations reduce peaks and stress hours.")

    try:
        demand_hourly = get_state_hourly()
    except FileNotFoundError as e:
        st.error(str(e))
        st.stop()

    states = list_states()
    start, end = date_range()

    with st.sidebar:
        st.subheader("What‑If Controls")
        selected_state = st.selectbox("State", options=states, index=states.index("CA") if "CA" in states else 0)
        years = st.multiselect("Years", options=list(range(start.year, end.year + 1)), default=[end.year])
        storage_power = st.number_input("Storage power (MW)", min_value=0.0, max_value=20000.0, value=1000.0, step=50.0)
        storage_hours = st.number_input("Storage duration (hours)", min_value=0.0, max_value=48.0, value=4.0, step=1.0)
        dr_power = st.number_input("Demand response max (MW)", min_value=0.0, max_value=20000.0, value=500.0, step=50.0)
        dr_hours = st.number_input("DR hours per day", min_value=0, max_value=24, value=3, step=1)
        percentile = st.slider("Stress percentile for threshold", 90, 99, 95)

    filtered = filter_states_years(demand_hourly, states=[selected_state], years=years)
    if filtered.empty:
        st.warning("No data for selection.")
        return

    series = filtered[selected_state]

    # Simulate
    new_series, dispatch = simulate_counterfactual(series, storage_power, storage_hours, dr_power, dr_hours)

    # Metrics
    orig_peak_gw = series.max() / 1000.0
    new_peak_gw = new_series.max() / 1000.0
    peak_reduction_gw = orig_peak_gw - new_peak_gw

    threshold_mw = series.quantile(percentile / 100.0)
    orig_stress_hours = (series >= threshold_mw).sum()
    new_stress_hours = (new_series >= threshold_mw).sum()
    prevented_stress_hours = orig_stress_hours - new_stress_hours

    # Summary cards
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Original peak", f"{orig_peak_gw:.2f} GW")
    c2.metric("New peak", f"{new_peak_gw:.2f} GW")
    c3.metric("Peak reduction", f"{peak_reduction_gw:.2f} GW")
    c4.metric("Stress hours prevented", f"{int(prevented_stress_hours)}")

    # Time series compare: last N days window selector
    window_days = st.slider("Detail window (days)", 1, 60, 14)
    end = series.index.max()
    start_window = end - pd.Timedelta(days=window_days)
    view_idx = (series.index >= start_window)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=series[view_idx].index, y=series[view_idx] / 1000.0, mode="lines", name="Original demand", line=dict(color="#111827")))
    fig.add_trace(go.Scatter(x=new_series[view_idx].index, y=new_series[view_idx] / 1000.0, mode="lines", name="After DR+Storage", line=dict(color="#0f766e")))
    # show threshold
    fig.add_trace(go.Scatter(x=series[view_idx].index, y=[threshold_mw / 1000.0] * view_idx.sum(), mode="lines", name=f"{percentile}th pct threshold", line=dict(color="#f97316", dash="dash")))
    st.plotly_chart(common_layout(fig, f"{selected_state}: demand before/after (last {window_days} days)", "Demand (GW)", "Timestamp"), use_container_width=True)

    # Dispatch timeline
    if not dispatch.empty:
        disp = dispatch.copy()
        disp = disp.groupby([disp.index, "type"]).sum().unstack(fill_value=0)
        # normalize columns
        if ("mw", "dr") in disp.columns:
            drcol = ("mw", "dr")
        else:
            drcol = None
        if ("mw", "storage") in disp.columns:
            stcol = ("mw", "storage")
        else:
            stcol = None

        fig2 = go.Figure()
        if drcol is not None:
            fig2.add_trace(go.Bar(x=disp.index, y=disp[drcol], name="DR (MW)", marker_color="#ef4444"))
        if stcol is not None:
            fig2.add_trace(go.Bar(x=disp.index, y=disp[stcol], name="Storage discharge (MW)", marker_color="#2563eb"))
        st.plotly_chart(common_layout(fig2, "Mitigation dispatch timeline", "MW dispatched", "Timestamp", 360), use_container_width=True)
    else:
        st.info("No mitigation dispatch occurred with the current parameters.")


if __name__ == "__main__":
    main()
