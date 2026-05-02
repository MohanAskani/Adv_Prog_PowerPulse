"""Grid Stress page.

This module uses hourly demand to rank demand pressure, then adds monthly
generation context where the uploaded generation data can support it.
"""

from __future__ import annotations

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from powerpulse.data import get_generation_monthly, get_state_hourly, list_states, date_range
from powerpulse.stress import (
    DEFAULT_WEIGHTS,
    component_long_frame,
    monthly_stress_context,
    score_stress_components,
    stress_component_frame,
)
from powerpulse.transforms import filter_states_years


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
