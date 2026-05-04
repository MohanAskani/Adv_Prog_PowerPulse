"""Renewable Mismatch page.

State-level mismatch is measured by aligning hourly demand aggregates with
monthly state generation. County views show demand exposure because renewable
generation is not available at county resolution in the current data.
"""

from __future__ import annotations

import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from powerpulse.data import (
    get_counties_geojson,
    get_county_summary,
    get_generation_monthly,
    get_state_hourly,
    list_states,
    date_range,
)
from powerpulse.mismatch import monthly_mismatch_frame, state_mismatch_summary, worst_mismatch_months
from powerpulse.transforms import filter_states_years
from powerpulse.viz import county_choropleth


st.markdown(
    """
    <style>
    .block-container { padding-top: 1.1rem; padding-bottom: 2rem; }
    .mismatch-hero {
        background:
            radial-gradient(circle at 12% 18%, rgba(34, 197, 94, 0.28), transparent 34%),
            radial-gradient(circle at 88% 8%, rgba(14, 165, 233, 0.24), transparent 32%),
            linear-gradient(135deg, #052e16 0%, #134e4a 48%, #111827 100%);
        color: white;
        border-radius: 24px;
        padding: 1.5rem 1.6rem 1.35rem;
        margin-bottom: 1rem;
        box-shadow: 0 16px 40px rgba(15, 23, 42, 0.16);
    }
    .mismatch-hero h1 { margin: 0; font-size: 2.25rem; line-height: 1.05; }
    .mismatch-hero p { margin: .65rem 0 0; max-width: 78ch; color: rgba(255,255,255,.9); font-size: .98rem; }
    .mismatch-kicker {
        font-size: .74rem; font-weight: 800; letter-spacing: .19em;
        text-transform: uppercase; color: #bbf7d0; margin-bottom: .45rem;
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
    .mini-value { color: #111827; font-size: 1.45rem; font-weight: 850; line-height: 1.1; margin-top: .25rem; }
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


def common_layout(fig: go.Figure, title: str, y_title: str, x_title: str, height: int = 400) -> go.Figure:
    fig.update_layout(
        template="plotly_white",
        title=title,
        yaxis_title=y_title,
        xaxis_title=x_title,
        height=height,
        margin=dict(l=40, r=20, t=64, b=48),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
    )
    return fig


def pct(value: float | None) -> str:
    if value is None or value != value:
        return "n/a"
    return f"{value:.0%}"


st.markdown(
    """
    <div class="mismatch-hero">
      <div class="mismatch-kicker">PowerPulse</div>
      <h1>Renewable Mismatch</h1>
      <p>
        This module compares state demand with renewable generation at monthly
        resolution, then shows where county demand is concentrated inside each
        state. County charts are demand exposure views because generation is not
        county-level in the current data.
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)

try:
    demand_hourly = get_state_hourly()
    generation_monthly = get_generation_monthly()
    county_summary = get_county_summary()
except FileNotFoundError as e:
    st.error(str(e))
    st.stop()

all_states = list_states()
start, end = date_range()
all_years = list(range(start.year, end.year + 1))

with st.sidebar:
    st.subheader("Renewable Mismatch Controls")
    selected_states = st.multiselect(
        "States for ranking",
        options=all_states,
        default=["CA", "TX", "NY", "FL", "AZ"],
        help="Choose states to include in state-level mismatch charts. Empty means all states.",
    )
    selected_years = st.multiselect("Years", options=all_years, default=all_years)
    county_metric = st.radio(
        "County map metric",
        options=["Average demand", "Demand per 100k people"],
        index=0,
    )

states_for_query = selected_states or all_states
years_for_query = selected_years or all_years
filtered = filter_states_years(demand_hourly, states=states_for_query, years=years_for_query)

if filtered.empty:
    st.warning("No demand records match the current filters.")
    st.stop()

monthly = monthly_mismatch_frame(filtered, generation_monthly)
if monthly.empty:
    st.warning("Demand and generation data did not overlap for the current filters.")
    st.stop()

summary = state_mismatch_summary(monthly)

state_tab, county_tab = st.tabs(["State Renewable Mismatch", "County Demand Exposure"])

with state_tab:
    selected_state = st.selectbox(
        "State detail",
        options=summary["state"].tolist(),
        index=0,
        help="The detail charts below use this state.",
    )
    selected_summary = summary.loc[summary["state"] == selected_state].iloc[0]
    state_monthly = monthly[monthly["state"] == selected_state].sort_values("date")

    cards = st.columns(5)
    with cards[0]:
        metric_card("Mismatch score", f"{selected_summary['mismatch_score']:.1f}")
    with cards[1]:
        metric_card("High-month renewable share", pct(selected_summary["high_month_renewable_share"]))
    with cards[2]:
        metric_card("Avg renewable/demand", pct(selected_summary["avg_renewable_to_demand"]))
    with cards[3]:
        metric_card("Avg gap", f"{selected_summary['avg_gap_twh']:.1f} TWh")
    with cards[4]:
        metric_card("Peak monthly demand", f"{selected_summary['peak_monthly_demand_twh']:.1f} TWh")

    with st.expander("How the mismatch score is computed", expanded=False):
        st.write(
            "Demand is hourly MW summed into monthly MWh. Generation is monthly MWh. "
            "For each state, months above that state's 75th percentile demand are labeled high-demand months. "
            "The score combines high-month renewable gap ratio, low high-month renewable share, and peak monthly demand. "
            "It is a transparent comparison score, not an official grid reliability metric."
        )

    with st.container(border=True):
        section_header(
            1,
            "All-state mismatch ranking",
            "Higher scores mean high-demand months coincide with larger renewable coverage gaps.",
        )
        left, right = st.columns([1.1, 1])
        with left:
            ranking = summary.head(15).sort_values("mismatch_score")
            fig = px.bar(
                ranking,
                x="mismatch_score",
                y="state",
                orientation="h",
                color="mismatch_score",
                color_continuous_scale="Tealgrn",
                text="mismatch_score",
            )
            fig.update_traces(texttemplate="%{text:.1f}", textposition="outside")
            st.plotly_chart(common_layout(fig, "Highest renewable mismatch states", "State", "Mismatch score"), width="stretch")
        with right:
            show_cols = [
                "state",
                "mismatch_score",
                "avg_monthly_demand_twh",
                "avg_renewable_share",
                "high_month_renewable_share",
                "avg_renewable_to_demand",
                "avg_gap_twh",
            ]
            st.dataframe(
                summary[show_cols].style.format(
                    {
                        "mismatch_score": "{:.1f}",
                        "avg_monthly_demand_twh": "{:.1f}",
                        "avg_renewable_share": "{:.0%}",
                        "high_month_renewable_share": "{:.0%}",
                        "avg_renewable_to_demand": "{:.0%}",
                        "avg_gap_twh": "{:.1f}",
                    }
                ),
                width="stretch",
                hide_index=True,
            )

    with st.container(border=True):
        section_header(
            2,
            "Monthly demand vs renewable generation",
            "This shows whether renewable generation rises with the demand months for the selected state.",
        )
        line_frame = state_monthly.melt(
            id_vars=["date"],
            value_vars=["demand_mwh", "renewable_generation_mwh", "total_generation_mwh"],
            var_name="series",
            value_name="mwh",
        )
        line_frame["series"] = line_frame["series"].map(
            {
                "demand_mwh": "Demand",
                "renewable_generation_mwh": "Renewable generation",
                "total_generation_mwh": "Total generation",
            }
        )
        fig = px.line(
            line_frame,
            x="date",
            y="mwh",
            color="series",
            color_discrete_map={
                "Demand": "#111827",
                "Renewable generation": "#16a34a",
                "Total generation": "#0ea5e9",
            },
        )
        st.plotly_chart(common_layout(fig, f"{selected_state}: monthly demand and generation", "MWh", "Month", 430), width="stretch")

    with st.container(border=True):
        section_header(
            3,
            "Peak demand vs renewable share",
            "Bars show monthly peak load; the line shows renewable share for the same month.",
        )
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(
            go.Bar(
                x=state_monthly["date"],
                y=state_monthly["peak_load_gw"],
                marker_color="#0f766e",
                name="Monthly peak load",
                hovertemplate="%{x|%b %Y}<br>%{y:.1f} GW<extra></extra>",
            ),
            secondary_y=False,
        )
        fig.add_trace(
            go.Scatter(
                x=state_monthly["date"],
                y=state_monthly["renewable_share"],
                mode="lines+markers",
                line=dict(color="#f97316", width=3),
                name="Renewable share",
                hovertemplate="%{x|%b %Y}<br>%{y:.0%}<extra></extra>",
            ),
            secondary_y=True,
        )
        fig.update_yaxes(title_text="Peak load (GW)", secondary_y=False)
        fig.update_yaxes(title_text="Renewable share", tickformat=".0%", secondary_y=True)
        st.plotly_chart(common_layout(fig, f"{selected_state}: peak load and renewable share", "Peak load (GW)", "Month", 430), width="stretch")

    with st.container(border=True):
        section_header(
            4,
            "Renewable gap over time",
            "The gap is estimated monthly demand minus renewable generation. Larger bars mean more demand is left outside renewable coverage.",
        )
        fig = px.bar(
            state_monthly,
            x="date",
            y="renewable_gap_mwh",
            color="demand_period",
            color_discrete_map={"High-demand month": "#dc2626", "Other month": "#94a3b8"},
        )
        st.plotly_chart(common_layout(fig, f"{selected_state}: renewable gap by month", "MWh", "Month", 400), width="stretch")

    with st.container(border=True):
        section_header(
            5,
            "Worst mismatch months",
            "Months ranked by renewable gap ratio for the selected state.",
        )
        worst = worst_mismatch_months(monthly, selected_state)
        st.dataframe(
            worst.style.format(
                {
                    "demand_mwh": "{:,.0f}",
                    "renewable_generation_mwh": "{:,.0f}",
                    "renewable_share": "{:.0%}",
                    "renewable_to_demand": "{:.0%}",
                    "renewable_gap_mwh": "{:,.0f}",
                    "gap_ratio": "{:.0%}",
                    "peak_load_gw": "{:.1f}",
                }
            ),
            width="stretch",
            hide_index=True,
        )

with county_tab:
    county_states = sorted(county_summary["state"].dropna().unique().tolist())
    default_county_index = county_states.index(selected_state) if selected_state in county_states else 0
    county_state = st.selectbox("County state", options=county_states, index=default_county_index)
    state_counties = county_summary[county_summary["state"] == county_state].copy()
    state_context = summary[summary["state"] == county_state]

    if state_counties.empty:
        st.warning("No counties found for this state.")
        st.stop()

    state_counties["avg_demand_gw"] = state_counties["avg_demand_mw"] / 1000
    state_counties["map_value"] = (
        state_counties["avg_demand_mw"]
        if county_metric == "Average demand"
        else state_counties["demand_per_100k_mw"]
    )

    cards = st.columns(4)
    with cards[0]:
        metric_card("Counties", f"{len(state_counties)}")
    with cards[1]:
        metric_card("Top county demand", f"{state_counties['avg_demand_gw'].max():.1f} GW")
    with cards[2]:
        metric_card("State county avg", f"{state_counties['avg_demand_gw'].mean():.2f} GW")
    with cards[3]:
        if not state_context.empty:
            metric_card("State mismatch score", f"{state_context.iloc[0]['mismatch_score']:.1f}")
        else:
            metric_card("State mismatch score", "n/a")

    with st.container(border=True):
        section_header(
            1,
            "Top counties by average demand",
            "These counties drive the largest average load within the selected state.",
        )
        top_demand = state_counties.nlargest(15, "avg_demand_mw").sort_values("avg_demand_mw")
        fig = px.bar(
            top_demand,
            x="avg_demand_gw",
            y="county_label",
            orientation="h",
            color="avg_demand_gw",
            color_continuous_scale="Tealgrn",
        )
        st.plotly_chart(common_layout(fig, f"{county_state}: highest average-demand counties", "County", "Average demand (GW)", 430), width="stretch")

    with st.container(border=True):
        section_header(
            2,
            "Top counties by demand intensity",
            "Per-capita demand highlights counties where load is high relative to population.",
        )
        top_intensity = state_counties.nlargest(15, "demand_per_100k_mw").sort_values("demand_per_100k_mw")
        fig = px.bar(
            top_intensity,
            x="demand_per_100k_mw",
            y="county_label",
            orientation="h",
            color="demand_per_100k_mw",
            color_continuous_scale="Oranges",
        )
        st.plotly_chart(common_layout(fig, f"{county_state}: highest demand per 100k people", "County", "MW per 100k people", 430), width="stretch")

    with st.container(border=True):
        section_header(
            3,
            "County demand distribution",
            "Distribution view for the selected state's county demand values.",
        )
        left, right = st.columns([1, 1])
        with left:
            fig = px.histogram(
                state_counties,
                x="avg_demand_gw",
                nbins=min(30, max(8, len(state_counties) // 2)),
                color_discrete_sequence=["#0f766e"],
            )
            st.plotly_chart(common_layout(fig, f"{county_state}: county average-demand distribution", "County count", "Average demand (GW)", 360), width="stretch")
        with right:
            fig = px.box(
                state_counties,
                y="demand_per_100k_mw",
                points="outliers",
                color_discrete_sequence=["#f97316"],
            )
            st.plotly_chart(common_layout(fig, f"{county_state}: demand intensity spread", "MW per 100k people", "", 360), width="stretch")

    with st.container(border=True):
        section_header(
            4,
            "County demand map",
            "Map colors show county demand exposure. Renewable mismatch remains state-level with the current generation data.",
        )
        try:
            counties_geojson = get_counties_geojson()
            color_bar = "Avg demand (MW)" if county_metric == "Average demand" else "MW per 100k people"
            fig = county_choropleth(
                state_counties,
                counties_geojson,
                f"{county_state}: county demand exposure",
                "map_value",
                color_bar,
            )
            st.plotly_chart(fig, width="stretch")
        except FileNotFoundError as e:
            st.info(str(e))

    with st.container(border=True):
        section_header(
            5,
            "County data table",
            "Sortable county demand metrics for the selected state.",
        )
        show_cols = [
            "fips",
            "county_label",
            "avg_demand_mw",
            "population",
            "demand_per_capita_mw",
            "demand_per_100k_mw",
        ]
        st.dataframe(
            state_counties[show_cols]
            .sort_values("avg_demand_mw", ascending=False)
            .style.format(
                {
                    "avg_demand_mw": "{:,.1f}",
                    "population": "{:,.0f}",
                    "demand_per_capita_mw": "{:.6f}",
                    "demand_per_100k_mw": "{:.1f}",
                }
            ),
            width="stretch",
            hide_index=True,
        )
