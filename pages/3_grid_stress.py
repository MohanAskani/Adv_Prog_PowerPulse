"""Grid Stress page.

This module uses hourly demand to rank demand pressure, then adds monthly
generation context where the uploaded generation data can support it.
"""

from __future__ import annotations

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import pandas as pd

from powerpulse.data import get_generation_monthly, get_state_hourly, list_states, date_range
from powerpulse.stress import (
    DEFAULT_WEIGHTS,
    component_long_frame,
    monthly_stress_context,
    score_stress_components,
    stress_component_frame,
)
from powerpulse.transforms import filter_states_years
from powerpulse.viz import month_hour_heatmap


st.markdown(
    """
    <style>
    .block-container { padding-top: 1.1rem; padding-bottom: 2rem; }
    .stress-hero {
        background:
            radial-gradient(circle at 15% 15%, rgba(251, 146, 60, 0.34), transparent 34%),
            radial-gradient(circle at 85% 5%, rgba(20, 184, 166, 0.28), transparent 32%),
            linear-gradient(135deg, #111827 0%, #7c2d12 54%, #0f172a 100%);
        color: white;
        border-radius: 24px;
        padding: 1.5rem 1.6rem 1.35rem;
        margin-bottom: 1rem;
        box-shadow: 0 16px 40px rgba(15, 23, 42, 0.16);
    }
    .stress-hero h1 { margin: 0; font-size: 2.25rem; line-height: 1.05; }
    .stress-hero p { margin: .65rem 0 0; max-width: 78ch; color: rgba(255,255,255,.9); font-size: .98rem; }
    .stress-kicker {
        font-size: .74rem; font-weight: 800; letter-spacing: .19em;
        text-transform: uppercase; color: #fed7aa; margin-bottom: .45rem;
    }
    .section-tag {
        font-size: .72rem; font-weight: 800; letter-spacing: .16em;
        text-transform: uppercase; color: #0f766e; margin-bottom: .1rem;
    }
    .section-title { font-size: 1.35rem; font-weight: 800; color: #0f172a; margin-bottom: .15rem; }
    .section-note { color: #64748b; font-size: .95rem; margin-bottom: .55rem; }
    .mini-card {
        border: 1px solid #e2e8f0; border-radius: 18px; padding: .85rem .95rem;
        background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
    }
    .mini-label { color: #64748b; font-size: .78rem; font-weight: 700; text-transform: uppercase; letter-spacing: .08em; }
    .mini-value { color: #111827; font-size: 1.55rem; font-weight: 850; line-height: 1.1; margin-top: .25rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


def section_header(number: int, title: str, note: str) -> None:
    st.markdown(
        f"""
        <div class="section-tag">Section {number}</div>
        <div class="section-title">{title}</div>
        <div class="section-note">{note}</div>
        """,
        unsafe_allow_html=True,
    )


def metric_card(label: str, value: str) -> None:
    st.markdown(
        f"""
        <div class="mini-card">
          <div class="mini-label">{label}</div>
          <div class="mini-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def common_layout(fig: go.Figure, title: str, y_title: str, x_title: str, height: int = 390) -> go.Figure:
    fig.update_layout(
        template="plotly_white",
        title=title,
        yaxis_title=y_title,
        xaxis_title=x_title,
        height=height,
        margin=dict(l=40, r=20, t=64, b=44),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
    )
    return fig


st.markdown(
    """
    <div class="stress-hero">
      <div class="stress-kicker">PowerPulse</div>
      <h1>Grid Stress</h1>
      <p>
        This page ranks states by demand pressure using peak intensity,
        volatility, seasonality, ramping, and near-peak persistence. Monthly
        generation is added as context, not as an official reliability measure.
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)

try:
    demand_hourly = get_state_hourly()
except FileNotFoundError as e:
    st.error(str(e))
    st.stop()

try:
    generation_monthly = get_generation_monthly()
except FileNotFoundError:
    generation_monthly = None
    st.warning("Monthly generation aggregate is missing, so supply context is hidden.")

all_states = list_states()
start, end = date_range()
all_years = list(range(start.year, end.year + 1))

with st.sidebar:
    st.subheader("Grid Stress Controls")
    selected_states = st.multiselect(
        "States",
        options=all_states,
        default=["CA", "TX", "NY", "FL", "AZ"],
        help="Choose states to compare. Leave empty to rank all states.",
    )
    selected_years = st.multiselect("Years", options=all_years, default=all_years)
    st.divider()
    st.caption("Score weights")
    weights = {
        "peak_intensity": st.slider("Peak intensity", 0, 50, DEFAULT_WEIGHTS["peak_intensity"]),
        "volatility": st.slider("Volatility", 0, 50, DEFAULT_WEIGHTS["volatility"]),
        "seasonal_extreme": st.slider("Seasonal extreme", 0, 50, DEFAULT_WEIGHTS["seasonal_extreme"]),
        "ramp_severity": st.slider("Ramp severity", 0, 50, DEFAULT_WEIGHTS["ramp_severity"]),
        "near_peak_persistence": st.slider("Near-peak persistence", 0, 50, DEFAULT_WEIGHTS["near_peak_persistence"]),
    }

states_for_query = selected_states or all_states
years_for_query = selected_years or all_years
filtered = filter_states_years(demand_hourly, states=states_for_query, years=years_for_query)

if filtered.empty:
    st.warning("No demand records match the current filters.")
    st.stop()

components = stress_component_frame(filtered)
scored = score_stress_components(components, weights)
top_state = scored.iloc[0]

cards = st.columns(4)
with cards[0]:
    metric_card("Highest stress state", str(top_state["state"]))
with cards[1]:
    metric_card("Stress score", f"{top_state['stress_score']:.1f}")
with cards[2]:
    metric_card("Peak load", f"{top_state['peak_load_gw']:.1f} GW")
with cards[3]:
    metric_card("States ranked", f"{len(scored)}")

with st.expander("How the stress score is computed", expanded=False):
    st.write(
        "Each component is percentile-ranked across selected states, then combined with the sidebar weights. "
        "Peak intensity = 99th percentile load / average load. Volatility = daily peak variation. "
        "Seasonal extreme = summer peak / shoulder-season baseline. Ramp severity = large hourly changes. "
        "Near-peak persistence = share of hours above 90% of the state peak."
    )

with st.container(border=True):
    section_header(
        1,
        "State stress ranking",
        "A transparent state ranking based only on demand behavior. Higher means the selected period shows more concentrated or variable load pressure.",
    )
    left, right = st.columns([1.1, 1])
    with left:
        fig = px.bar(
            scored.head(15).sort_values("stress_score"),
            x="stress_score",
            y="state",
            orientation="h",
            color="stress_score",
            color_continuous_scale="Oranges",
            text="stress_score",
        )
        fig.update_traces(texttemplate="%{text:.1f}", textposition="outside")
        st.plotly_chart(common_layout(fig, "Top stress states", "State", "Stress score"), use_container_width=True)
    with right:
        show_cols = [
            "state",
            "stress_score",
            "peak_load_gw",
            "peak_intensity",
            "volatility",
            "seasonal_extreme",
            "ramp_severity",
            "near_peak_persistence",
        ]
        st.dataframe(
            scored[show_cols].style.format(
                {
                    "stress_score": "{:.1f}",
                    "peak_load_gw": "{:.1f}",
                    "peak_intensity": "{:.2f}",
                    "volatility": "{:.2f}",
                    "seasonal_extreme": "{:.2f}",
                    "ramp_severity": "{:.3f}",
                    "near_peak_persistence": "{:.1%}",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

with st.container(border=True):
    section_header(
        2,
        "Why states rank high",
        "Component scores explain the ranking so users can see whether stress is driven by peaks, variability, seasonality, ramps, or persistence.",
    )
    top_n = scored.head(8)
    comp_long = component_long_frame(top_n)
    fig = px.bar(
        comp_long,
        x="state",
        y="component_score",
        color="component",
        barmode="group",
        color_discrete_sequence=["#9a3412", "#ea580c", "#f97316", "#14b8a6", "#2563eb"],
    )
    st.plotly_chart(common_layout(fig, "Component scores for top-ranked states", "Component score", "State", 430), use_container_width=True)

with st.container(border=True):
    section_header(
        3,
        "Monthly demand and generation context",
        "Generation is monthly, so this section compares monthly demand MWh with monthly total and renewable generation MWh.",
    )
    monthly = monthly_stress_context(filtered, generation_monthly)
    if generation_monthly is None:
        st.info("Add generation_monthly.parquet to show generation context.")
    else:
        selected_for_monthly = st.selectbox(
            "State for monthly context",
            options=scored["state"].tolist(),
            index=0,
        )
        state_monthly = monthly[monthly["state"] == selected_for_monthly].copy()
        state_monthly = state_monthly.sort_values("date")

        m1, m2, m3 = st.columns(3)
        latest = state_monthly.dropna(subset=["total_generation_mwh"]).tail(1)
        if not latest.empty:
            row = latest.iloc[0]
            with m1:
                metric_card("Latest gen/demand", f"{row['generation_to_demand']:.0%}")
            with m2:
                metric_card("Renewable/demand", f"{row['renewable_to_demand']:.0%}")
            with m3:
                metric_card("Renewable share", f"{row['renewable_share']:.0%}")

        line_frame = state_monthly.melt(
            id_vars=["date"],
            value_vars=["demand_mwh", "total_generation_mwh", "renewable_generation_mwh"],
            var_name="series",
            value_name="mwh",
        )
        labels = {
            "demand_mwh": "Demand",
            "total_generation_mwh": "Total generation",
            "renewable_generation_mwh": "Renewable generation",
        }
        line_frame["series"] = line_frame["series"].map(labels)
        fig = px.line(
            line_frame,
            x="date",
            y="mwh",
            color="series",
            color_discrete_map={
                "Demand": "#111827",
                "Total generation": "#0f766e",
                "Renewable generation": "#22c55e",
            },
        )
        st.plotly_chart(
            common_layout(fig, f"{selected_for_monthly}: monthly demand vs generation", "MWh", "Month", 430),
            use_container_width=True,
        )

with st.container(border=True):
    section_header(
        4,
        "Seasonal and ramp pressure",
        "These views show when stress appears, using hourly demand rolled into monthly peaks and large hourly changes.",
    )
    selected_detail = st.selectbox(
        "State for stress timeline",
        options=scored["state"].tolist(),
        index=0,
        key="detail_state",
    )
    state_series = filtered[selected_detail]
    monthly_peak = state_series.resample("MS").max() / 1000
    ramp95 = state_series.diff().abs().resample("MS").quantile(0.95) / 1000

    left, right = st.columns(2)
    with left:
        fig = go.Figure(
            go.Scatter(
                x=monthly_peak.index,
                y=monthly_peak.values,
                mode="lines+markers",
                line=dict(color="#ea580c", width=3),
                name="Monthly peak",
            )
        )
        st.plotly_chart(common_layout(fig, f"{selected_detail}: monthly peak load", "Peak load (GW)", "Month"), use_container_width=True)
    with right:
        fig = go.Figure(
            go.Bar(
                x=ramp95.index,
                y=ramp95.values,
                marker_color="#0f766e",
                name="95th percentile hourly ramp",
            )
        )
        st.plotly_chart(common_layout(fig, f"{selected_detail}: monthly ramp severity", "Hourly change (GW)", "Month"), use_container_width=True)

    # --- Section 5: Ramp Pressure Explorer (interactive deep-dive) ---
with st.container(border=True):
    section_header(
        5,
        "Ramp Events Explorer",
        "Inspect large hourly ramps and seasonal patterns; optionally overlay local weather for context.",
    )

    selected_ramp_state = st.selectbox(
        "State for ramp explorer",
        options=scored["state"].tolist(),
        index=0,
        key="ramp_detail_state",
    )

    # Hourly series for the selected state (MW)
    state_series_r = filtered[selected_ramp_state]
    if state_series_r.empty:
        st.warning("No hourly data for the selected state and filters.")
    else:
        # Ramp series in GW
        ramp_gw = state_series_r.diff().abs() / 1000.0

        # Month×hour heatmap of average ramp magnitude
        pivot = (
            ramp_gw.rename("ramp_gw").to_frame()
            .assign(month=lambda df: df.index.month, hour=lambda df: df.index.hour)
            .groupby(["month", "hour"])["ramp_gw"]
            .mean()
            .unstack(fill_value=0)
        )
        pivot = pivot.reindex(index=range(1, 13), columns=range(24), fill_value=0)

        st.markdown("**Monthly × Hour ramp intensity**")
        st.plotly_chart(month_hour_heatmap(pivot, f"{selected_ramp_state}: average hourly ramp (GW) by month"), use_container_width=True)

        # Top-N ramp events
        st.markdown("**Top ramp events**")
        cols = st.columns([1, 1, 1])
        with cols[0]:
            top_n = st.number_input("Top N events", min_value=3, max_value=50, value=8, step=1, key="ramp_top_n")
        with cols[1]:
            event_window = st.slider("Detail window (hours each side)", 6, 72, 24, key="ramp_window")
        with cols[2]:
            min_ramp = st.slider("Min ramp threshold (GW)", 0.0, float(ramp_gw.max() if not ramp_gw.empty else 10.0), 0.0, 0.1, key="ramp_min")

        events = ramp_gw.dropna()
        if min_ramp > 0:
            events = events[events >= min_ramp]
        if events.empty:
            st.info("No ramp events match the current threshold/time filters.")
        else:
            top_events = events.nlargest(top_n).reset_index()
            top_events.columns = ["timestamp", "ramp_gw"]

            fig_events = px.bar(
                top_events,
                x="timestamp",
                y="ramp_gw",
                color="ramp_gw",
                color_continuous_scale="Turbo",
                title=f"Top {len(top_events)} hourly absolute ramps for {selected_ramp_state}",
            )
            fig_events.update_traces(hovertemplate="%{x}<br>Ramp %{y:.2f} GW<extra></extra>")
            st.plotly_chart(common_layout(fig_events, fig_events.layout.title.text, "Ramp (GW)", "Timestamp", 360), use_container_width=True)

            # Select an event to inspect
            options = [f"{r['timestamp']} — {r['ramp_gw']:.2f} GW" for _, r in top_events.iterrows()]
            choice = st.selectbox("Inspect event", options=options, key="ramp_choice")
            chosen_idx = options.index(choice)
            ts = top_events.loc[chosen_idx, "timestamp"]

            # Show detailed +/- window around the event
            start = ts - pd.Timedelta(hours=event_window)
            end = ts + pd.Timedelta(hours=event_window)
            detail = state_series_r.loc[start:end] / 1000.0

            fig_detail = go.Figure()
            fig_detail.add_trace(go.Scatter(x=detail.index, y=detail.values, mode="lines+markers", name="Demand (GW)", line=dict(color="#111827", width=3)))
            # Overlay ramp as bar
            detail_ramp = detail.diff().abs()
            fig_detail.add_trace(go.Bar(x=detail_ramp.index, y=detail_ramp.values, name="Ramp (GW)", marker_color="#f97316", opacity=0.6, yaxis="y2"))
            fig_detail.update_layout(
                yaxis=dict(title="Demand (GW)"),
                yaxis2=dict(title="Ramp (GW)", overlaying="y", side="right", showgrid=False),
                hovermode="x unified",
            )
            st.plotly_chart(common_layout(fig_detail, f"Event detail: {ts} ({selected_ramp_state})", "Demand (GW)", "Timestamp", 420), use_container_width=True)

            # Optional weather upload to overlay temperature
            st.markdown("**Optional: upload weather CSV (timestamp, temperature)**")
            uploaded = st.file_uploader("Weather CSV for overlay (optional)", type=["csv"], key="ramp_weather_upload")
            if uploaded is not None:
                try:
                    import pandas as _pd

                    weather = _pd.read_csv(uploaded, parse_dates=[0], header=0)
                    weather.columns = ["timestamp", "temperature"] + list(weather.columns[2:])
                    weather = weather.set_index("timestamp").sort_index()
                    wdetail = weather["temperature"].loc[start:end]
                    if not wdetail.empty:
                        fig_detail.add_trace(go.Scatter(x=wdetail.index, y=wdetail.values, mode="lines", name="Temp (°C)", line=dict(color="#2563eb", dash="dot"), yaxis="y3"))
                        fig_detail.update_layout(yaxis3=dict(title="Temperature (°C)", anchor="free", overlaying="y", side="left", position=0.05))
                        st.plotly_chart(common_layout(fig_detail, f"Event detail + weather: {ts} ({selected_ramp_state})", "Demand (GW)", "Timestamp", 460), use_container_width=True)
                except Exception as e:
                    st.warning(f"Could not parse weather file: {e}")

        # Scatter: monthly average ramp vs renewable share (if monthly generation exists)
        if generation_monthly is None:
            st.info("Monthly generation data not available — upload `generation_monthly.parquet` to see ramp vs renewable scatter.")
        else:
            # monthly variable created earlier in Section 3; recompute per-state monthly if needed
            state_monthly = monthly[monthly["state"] == selected_ramp_state].copy()
            # compute avg ramp per month
            ramp_month = ramp_gw.to_frame(name="ramp_gw").assign(month=lambda df: df.index.month)
            ramp_month = ramp_month.groupby("month").mean().reindex(range(1, 13))
            scatter_df = state_monthly.merge(ramp_month.reset_index(), left_on=state_monthly["date"].dt.month, right_on="month", how="inner")
            scatter_df = scatter_df.rename(columns={"ramp_gw": "avg_ramp_gw"})
            fig_scatter = px.scatter(
                scatter_df,
                x="renewable_to_demand",
                y="avg_ramp_gw",
                color="date",
                labels={"renewable_to_demand": "Renewable / Demand", "avg_ramp_gw": "Avg hourly ramp (GW)"},
                title=f"{selected_ramp_state}: monthly avg ramp vs renewable/demand",
            )
            st.plotly_chart(common_layout(fig_scatter, fig_scatter.layout.title.text, "Avg ramp (GW)", "Renewable / Demand", 420), use_container_width=True)

    # --- Section 6: What-If simulator ---
with st.container(border=True):
    section_header(
        6,
        "Grid-stress simulator",
        "Simulate simple mitigations (battery discharge and DR) and see peak reduction and prevented stress hours.",
    )

    # Short, plain-language intro for users unfamiliar with batteries/grids
    st.markdown(
        """
        **About this simulator**

        - Try two simple actions: automatic demand cuts (DR) and battery discharge.
        - DR reduces the highest-demand hours; batteries discharge into the top hours until daily energy is used up.
        - For clear results, use the stress percentile around 90–95 (this counts the high-demand hours we aim to reduce).
        - You will see original vs. new peak, peak reduction, prevented stress hours, and a daily dispatch timeline.

        This is a quick scenario tool, not a full power-system model.
        """,
        unsafe_allow_html=True,
    )

    # Controls (local to section)
    sc1, sc2 = st.columns([1, 2])
    with sc1:
        w_state = st.selectbox("State for simulation", options=scored["state"].tolist(), index=0, key="whatif_state")
        w_years = st.multiselect("Years", options=all_years, default=[all_years[-1]], key="whatif_years")
        storage_power = st.number_input("Storage power (MW)", min_value=0.0, max_value=20000.0, value=1000.0, step=50.0, key="whatif_storage_power")
        storage_hours = st.number_input("Storage duration (hours)", min_value=0.0, max_value=48.0, value=4.0, step=1.0, key="whatif_storage_hours")
        dr_power = st.number_input("DR max (MW)", min_value=0.0, max_value=20000.0, value=500.0, step=50.0, key="whatif_dr_power")
        dr_hours = st.number_input("DR hours/day", min_value=0, max_value=24, value=3, step=1, key="whatif_dr_hours")
        pct = st.slider("Stress percentile (0-100%)", 0, 100, 95, key="whatif_stress_pct")
        st.caption("Percentile of historical hourly demand: 0% = lowest observed hour, 100% = highest observed hour (peak). Typical values: 90–95%.")
        # Critical threshold indicator
        critical_pct = 80
        st.markdown(f"**Critical level:** {critical_pct}% — hours at or above this are high stress.")
        if pct >= critical_pct:
            st.warning(f"Selected stress = {pct}% (≥ {critical_pct}%). This focuses the simulation on very high-demand hours.")
        else:
            st.info(f"Selected stress = {pct}% (< {critical_pct}%) — includes less extreme high-demand hours.")

    with sc2:
        # Run simulation
        if st.button("Run simulation", key="run_whatif"):
            sim_filtered = filter_states_years(demand_hourly, states=[w_state], years=w_years)
            if sim_filtered.empty:
                st.warning("No data for selection.")
            else:
                series_sim = sim_filtered[w_state]

                def simulate_counterfactual_local(series_mw: pd.Series, storage_power_mw: float, storage_hours: float, dr_power_mw: float, dr_hours_per_day: int):
                    df = series_mw.copy().to_frame(name="demand_mw")
                    df["date"] = df.index.normalize()
                    dispatch_records = []
                    energy_capacity_mwh = storage_power_mw * storage_hours
                    out = df["demand_mw"].copy()
                    for date, group in df.groupby("date"):
                        demands = group["demand_mw"].copy()
                        if dr_power_mw > 0 and dr_hours_per_day > 0:
                            top_hours = demands.nlargest(dr_hours_per_day).index
                            for h in top_hours:
                                red = min(dr_power_mw, out.loc[h])
                                out.loc[h] = out.loc[h] - red
                                dispatch_records.append({"timestamp": h, "type": "dr", "mw": red})
                        energy_left_mwh = energy_capacity_mwh
                        for h in demands.sort_values(ascending=False).index:
                            if energy_left_mwh <= 0 or storage_power_mw <= 0:
                                break
                            avail = min(storage_power_mw, out.loc[h])
                            use_mwh = min(avail, energy_left_mwh)
                            use_mw = use_mwh
                            out.loc[h] = out.loc[h] - use_mw
                            energy_left_mwh -= use_mwh
                            if use_mw > 0:
                                dispatch_records.append({"timestamp": h, "type": "storage", "mw": use_mw})
                    dispatch = pd.DataFrame(dispatch_records)
                    if not dispatch.empty:
                        dispatch = dispatch.set_index("timestamp").sort_index()
                    else:
                        dispatch = pd.DataFrame(columns=["type", "mw"]) 
                    return out, dispatch

                new_series_sim, dispatch_sim = simulate_counterfactual_local(series_sim, storage_power, storage_hours, dr_power, dr_hours)
                orig_peak = series_sim.max() / 1000.0
                new_peak = new_series_sim.max() / 1000.0
                peak_red = orig_peak - new_peak
                thresh = series_sim.quantile(pct / 100.0)
                orig_hours = (series_sim >= thresh).sum()
                new_hours = (new_series_sim >= thresh).sum()
                prevented = orig_hours - new_hours

                d1, d2, d3, d4 = st.columns(4)
                d1.metric("Orig peak", f"{orig_peak:.2f} GW")
                d2.metric("New peak", f"{new_peak:.2f} GW")
                d3.metric("Peak reduction", f"{peak_red:.2f} GW")
                d4.metric("Stress hours prevented", f"{int(prevented)}")

                # Plot last 14 days by default
                wnd = 14
                end_idx = series_sim.index.max()
                start_idx = end_idx - pd.Timedelta(days=wnd)
                idx = series_sim.index >= start_idx
                fig_sim = go.Figure()
                fig_sim.add_trace(go.Scatter(x=series_sim[idx].index, y=series_sim[idx] / 1000.0, mode="lines", name="Original"))
                fig_sim.add_trace(go.Scatter(x=new_series_sim[idx].index, y=new_series_sim[idx] / 1000.0, mode="lines", name="After"))
                fig_sim.add_trace(go.Scatter(x=series_sim[idx].index, y=[thresh / 1000.0] * idx.sum(), mode="lines", name=f"{pct}th pct", line=dict(dash="dash")))
                st.plotly_chart(common_layout(fig_sim, f"{w_state}: before/after (last {wnd} days)", "Demand (GW)", "Timestamp"), use_container_width=True)

                if not dispatch_sim.empty:
                    disp = dispatch_sim.copy()
                    if "mw" in disp.columns:
                        # Aggregate dispatch by day and type for a cleaner timeline
                        daily = disp.groupby([disp.index.normalize(), "type"])["mw"].sum().unstack(fill_value=0)
                        figd = go.Figure()
                        if "dr" in daily.columns:
                            figd.add_trace(go.Bar(x=daily.index, y=daily["dr"], name="DR (MW)", marker_color="#ef4444"))
                        if "storage" in daily.columns:
                            figd.add_trace(go.Bar(x=daily.index, y=daily["storage"], name="Storage (MW)", marker_color="#2563eb"))
                        if figd.data:
                            st.plotly_chart(common_layout(figd, "Mitigation dispatch timeline", "MW dispatched", "Date", 360), use_container_width=True)
                        else:
                            st.info("No dispatch recorded for the selected scenario.")
                    else:
                        st.info("No dispatch values found in simulation results.")

