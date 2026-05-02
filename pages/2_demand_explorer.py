"""Demand Explorer page (owner: Mohan).

This page presents the demand story in a clear order:
yearly trend, daily cycle, weekday/weekend, monthly/seasonal views,
month-hour heatmaps, volatility/extreme peaks, geography, and cross-country
context. The current filtering controls apply to the demand time-series
sections; the geography section uses the full U.S. summaries for comparison.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from powerpulse.data import (
    get_country_energy,
    get_counties_geojson,
    get_county_summary,
    get_state_hourly,
    get_state_summary,
    list_states,
    date_range,
)
from powerpulse.transforms import (
    aggregate_total_series,
    annual_peak_gw,
    annual_volatility_gw,
    country_comparison_frame,
    extreme_hours_frame,
    filter_states_years,
    hour_of_day_average,
    hour_of_day_per_state,
    month_hour_heatmap,
    monthly_average_gw,
    monthly_boxplot_frame,
    seasonal_average_gw,
    weekday_weekend_hourly,
    yearly_boxplot_frame,
    yearly_energy_twh,
)
from powerpulse.viz import (
    county_choropleth,
    country_scatter,
    country_trend,
    hour_of_day_by_state,
    hour_of_day_total,
    month_boxplot,
    month_hour_heatmap as viz_month_hour_heatmap,
    monthly_trend,
    seasonal_bar,
    state_choropleth,
    top_counties_bar,
    weekday_weekend_gap,
    weekday_weekend_lines,
    yearly_boxplot,
    yearly_energy_trend,
    yearly_peak_line,
    yearly_volatility,
)


st.markdown(
    """
    <style>
    .block-container {
        padding-top: 1.1rem;
        padding-bottom: 2rem;
    }
    .pp-hero {
        background:
            radial-gradient(circle at top left, rgba(14, 165, 233, 0.24), transparent 42%),
            linear-gradient(135deg, #0f172a 0%, #134e4a 48%, #1e293b 100%);
        color: white;
        border-radius: 24px;
        padding: 1.5rem 1.6rem 1.35rem 1.6rem;
        margin-bottom: 1rem;
        box-shadow: 0 16px 40px rgba(15, 23, 42, 0.16);
    }
    .pp-hero h1 {
        margin: 0;
        font-size: 2.3rem;
        line-height: 1.05;
    }
    .pp-hero p {
        margin-top: 0.65rem;
        margin-bottom: 0;
        max-width: 70ch;
        color: rgba(255, 255, 255, 0.9);
        font-size: 0.98rem;
    }
    .pp-kicker {
        font-size: 0.74rem;
        font-weight: 800;
        letter-spacing: 0.19em;
        text-transform: uppercase;
        color: #7dd3fc;
        margin-bottom: 0.45rem;
    }
    .pp-section-tag {
        font-size: 0.72rem;
        font-weight: 800;
        letter-spacing: 0.16em;
        text-transform: uppercase;
        color: #0f766e;
        margin-bottom: 0.1rem;
    }
    .pp-section-title {
        font-size: 1.45rem;
        font-weight: 800;
        color: #0f172a;
        margin-bottom: 0.15rem;
    }
    .pp-section-note {
        color: #64748b;
        font-size: 0.95rem;
        margin-bottom: 0.55rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def section_header(number: int, title: str, note: str) -> None:
    st.markdown(
        f"""
        <div class="pp-section-tag">Section {number}</div>
        <div class="pp-section-title">{title}</div>
        <div class="pp-section-note">{note}</div>
        """,
        unsafe_allow_html=True,
    )


def chart_definition(text: str) -> None:
    st.caption(text)


st.markdown(
    """
    <div class="pp-hero">
      <div class="pp-kicker">PowerPulse</div>
      <h1>Demand Explorer</h1>
      <p>
        This is the full interactive version of the demand analysis:
        annual trend, daily cycle, weekday/weekend behavior, seasonal structure,
        month-hour heatmaps, volatility, geography, and cross-country context.
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Data load (cached)
# ---------------------------------------------------------------------------
try:
    demand_hourly = get_state_hourly()
except FileNotFoundError as e:
    st.error(str(e))
    st.stop()

all_states = list_states()
start, end = date_range()
all_years = list(range(start.year, end.year + 1))


# ---------------------------------------------------------------------------
# Sidebar controls
# ---------------------------------------------------------------------------
with st.sidebar:
    st.subheader("Filters")
    selected_states = st.multiselect(
        "States",
        options=all_states,
        default=["CA", "TX", "NY"],
        help="Choose one or more states for the time-series sections.",
    )
    selected_years = st.multiselect(
        "Years",
        options=all_years,
        default=all_years,
        help="Filter the years used in the time-series sections.",
    )
    daily_view_mode = st.radio(
        "Daily cycle view",
        options=["Aggregate", "Per state"],
        index=0,
        help="Show the hourly load curve as a national/region total or one line per state.",
    )
    st.caption("All time-series charts use UTC because the raw county data is UTC-indexed.")


states_for_query = selected_states or all_states
years_for_query = selected_years or all_years
filtered = filter_states_years(demand_hourly, states=states_for_query, years=years_for_query)

if filtered.empty:
    st.warning("No rows match the current filter set. Widen the years or states selection.")
    st.stop()

aggregate_mw = aggregate_total_series(filtered)
aggregate_gw = aggregate_mw / 1e3
annual_peaks = annual_peak_gw(filtered)
label = "all states" if not selected_states else ", ".join(selected_states)

top_metrics = st.columns(4)
top_metrics[0].metric("States in view", len(states_for_query))
top_metrics[1].metric("Years in view", f"{min(years_for_query)}–{max(years_for_query)}")
top_metrics[2].metric("Peak load", f"{aggregate_gw.max():.1f} GW")
top_metrics[3].metric("Average load", f"{aggregate_gw.mean():.1f} GW")


# ---------------------------------------------------------------------------
# 1. Yearly trend
# ---------------------------------------------------------------------------
with st.container(border=True):
    section_header(
        1,
        "Yearly trend",
        "Annual energy plus yearly demand distributions. This shows how total demand changes year to year and how the hourly spread behaves.",
    )
    yearly_energy = yearly_energy_twh(filtered)
    yearly_box = yearly_boxplot_frame(filtered)

    left, right = st.columns(2)
    with left:
        chart_definition("Annual energy: total electricity demand summed across all hours in each year, shown in TWh.")
        st.plotly_chart(
            yearly_energy_trend(
                yearly_energy,
                title=f"Annual electricity demand for {label}",
            ),
            use_container_width=True,
        )
    with right:
        chart_definition("Hourly demand distribution: the spread of hourly values within each year, useful for spotting wider peaks and variability.")
        st.plotly_chart(
            yearly_boxplot(
                yearly_box,
                title=f"Hourly demand distribution by year for {label}",
            ),
            use_container_width=True,
        )

    if len(yearly_energy) >= 2:
        first_year = yearly_energy.iloc[0]
        last_year = yearly_energy.iloc[-1]
        delta_twh = last_year - first_year
        year_peak = int(annual_peaks.idxmax())
        year_metrics = st.columns(3)
        year_metrics[0].metric("First year", f"{first_year:.0f} TWh")
        year_metrics[1].metric("Latest year", f"{last_year:.0f} TWh", f"{delta_twh:+.0f} TWh")
        year_metrics[2].metric("Largest annual peak", f"{annual_peaks.max():.1f} GW", f"{year_peak}")


# ---------------------------------------------------------------------------
# 2. Daily cycle
# ---------------------------------------------------------------------------
with st.container(border=True):
    section_header(
        2,
        "Daily cycle",
        "The hour-of-day curve shows the typical daily load pattern and highlights when demand is highest and lowest.",
    )

    if daily_view_mode == "Aggregate":
        hour_series = hour_of_day_average(filtered, aggregator="sum")
        cycle_fig = hour_of_day_total(
            hour_series,
            title=f"Average demand by hour of day — {label}",
        )
    else:
        hour_series = hour_of_day_per_state(filtered)
        cycle_fig = hour_of_day_by_state(
            hour_series,
            title="Average demand by hour of day, per state",
        )

    chart_definition("Daily cycle: average demand by hour of day, either as a combined view or one line per state.")
    st.plotly_chart(cycle_fig, use_container_width=True)

    daily_aggregate = hour_of_day_average(filtered, aggregator="sum")
    peak_hour = int(daily_aggregate.idxmax())
    trough_hour = int(daily_aggregate.idxmin())
    peak_gw = daily_aggregate.max() / 1e3
    trough_gw = daily_aggregate.min() / 1e3
    swing_pct = 100 * (peak_gw - trough_gw) / trough_gw

    daily_metrics = st.columns(3)
    daily_metrics[0].metric("Peak hour (UTC)", f"{peak_hour:02d}:00", f"{peak_gw:.1f} GW")
    daily_metrics[1].metric("Trough hour (UTC)", f"{trough_hour:02d}:00", f"{trough_gw:.1f} GW")
    daily_metrics[2].metric("Peak vs trough", f"{swing_pct:.0f}%")


# ---------------------------------------------------------------------------
# 3. Weekday vs weekend
# ---------------------------------------------------------------------------
with st.container(border=True):
    section_header(
        3,
        "Weekday vs weekend",
        "This shows how work schedules shift demand across the day by comparing weekday and weekend patterns.",
    )
    ww_frame = weekday_weekend_hourly(filtered)
    weekday_pivot = ww_frame.pivot(index="hour_utc", columns="day_type", values="demand_gw").reindex(columns=["Weekday", "Weekend"])
    gap_series = weekday_pivot["Weekday"] - weekday_pivot["Weekend"]

    left, right = st.columns(2)
    with left:
        chart_definition("Weekday vs weekend lines: the average hourly demand curve for each day type.")
        st.plotly_chart(
            weekday_weekend_lines(
                ww_frame,
                title="Average hourly demand: weekday vs weekend",
            ),
            use_container_width=True,
        )
    with right:
        chart_definition("Weekday gap: the difference between weekday and weekend demand at each hour, in GW.")
        st.plotly_chart(
            weekday_weekend_gap(
                ww_frame,
                title="Weekday minus weekend demand by hour",
            ),
            use_container_width=True,
        )

    ww_metrics = st.columns(3)
    ww_metrics[0].metric("Weekday peak", f"{weekday_pivot['Weekday'].max():.1f} GW")
    ww_metrics[1].metric("Weekend peak", f"{weekday_pivot['Weekend'].max():.1f} GW")
    ww_metrics[2].metric("Largest gap hour", f"{int(gap_series.idxmax()):02d}:00", f"{gap_series.max():.1f} GW")


# ---------------------------------------------------------------------------
# 4. Monthly / seasonal
# ---------------------------------------------------------------------------
with st.container(border=True):
    section_header(
        4,
        "Monthly / seasonal",
        "Demand climbs into the summer and relaxes in spring/fall, which is easier to see when grouped by month and season.",
    )
    monthly = monthly_average_gw(filtered)
    seasonal = seasonal_average_gw(filtered)

    left, right = st.columns(2)
    with left:
        chart_definition("Monthly trend: average demand for each calendar month, showing the overall seasonal cycle.")
        st.plotly_chart(
            monthly_trend(
                monthly,
                title="Average demand by month",
            ),
            use_container_width=True,
        )
    with right:
        chart_definition("Seasonal bar: average demand grouped into winter, spring, summer, and autumn.")
        st.plotly_chart(
            seasonal_bar(
                seasonal,
                title="Average demand by season",
            ),
            use_container_width=True,
        )

    month_names = {1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun", 7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"}
    month_metrics = st.columns(2)
    month_metrics[0].metric("Highest month", month_names[int(monthly.idxmax())] if len(monthly) else "N/A")
    month_metrics[1].metric("Highest season", seasonal.idxmax() if len(seasonal) else "N/A")


# ---------------------------------------------------------------------------
# 5. Month-hour heatmap and boxplot
# ---------------------------------------------------------------------------
with st.container(border=True):
    section_header(
        5,
        "Month-hour heatmap and boxplot",
        "This is the densest view: where evening peaks line up with summer months and where the spread widens.",
    )
    heatmap = month_hour_heatmap(filtered)
    month_box = monthly_boxplot_frame(filtered)

    left, right = st.columns(2)
    with left:
        chart_definition("Heatmap: average demand for each month-hour combination, useful for spotting daily peaks by season.")
        st.plotly_chart(
            viz_month_hour_heatmap(
                heatmap,
                title="Average demand heatmap by month and hour",
            ),
            use_container_width=True,
        )
    with right:
        chart_definition("Monthly boxplot: the distribution of hourly demand within each month.")
        st.plotly_chart(
            month_boxplot(
                month_box,
                title="Hourly demand distribution by month",
            ),
            use_container_width=True,
        )


# ---------------------------------------------------------------------------
# 6. Volatility and extreme peaks
# ---------------------------------------------------------------------------
with st.container(border=True):
    section_header(
        6,
        "Volatility and extreme peaks",
        "This revisits the volatility pattern and the most extreme hours that cluster in summer.",
    )
    volatility = annual_volatility_gw(filtered)
    annual_peaks = annual_peak_gw(filtered)
    extreme_hours, threshold_gw = extreme_hours_frame(filtered, quantile=0.99)
    summer_share = 100 * extreme_hours["month"].isin([6, 7, 8]).mean() if not extreme_hours.empty else 0.0

    left, right = st.columns(2)
    with left:
        chart_definition("Volatility: yearly standard deviation of hourly demand, a simple measure of how uneven each year is.")
        st.plotly_chart(
            yearly_volatility(
                volatility,
                title="Yearly demand volatility",
            ),
            use_container_width=True,
        )
    with right:
        chart_definition("Annual peaks: the highest hourly demand reached in each year.")
        st.plotly_chart(
            yearly_peak_line(
                annual_peaks,
                title="Annual peak hourly demand",
            ),
            use_container_width=True,
        )

    vol_metrics = st.columns(3)
    vol_metrics[0].metric("99th percentile threshold", f"{threshold_gw:.1f} GW")
    vol_metrics[1].metric("Extreme hours", f"{len(extreme_hours):,}")
    vol_metrics[2].metric("Summer share of extremes", f"{summer_share:.0f}%")


# ---------------------------------------------------------------------------
# 7. Geography
# ---------------------------------------------------------------------------
with st.container(border=True):
    section_header(
        7,
        "County, state, and per-capita geography",
        "This section uses the full U.S. aggregates so the county and state maps stay comparable, independent of the time filters above.",
    )

    try:
        county_summary = get_county_summary().copy()
        state_summary = get_state_summary().copy()
        counties_geojson = get_counties_geojson()
    except FileNotFoundError as e:
        st.warning(str(e))
    else:
        county_summary["avg_demand_gw"] = county_summary["avg_demand_mw"] / 1000.0
        county_summary["demand_per_100k_gw"] = county_summary["demand_per_capita_mw"] * 100.0
        state_summary["avg_demand_gw"] = state_summary["avg_demand_mw"] / 1000.0
        state_summary["demand_per_100k_gw"] = state_summary["demand_per_capita_mw"] * 100.0

        county_top = county_summary.sort_values("avg_demand_mw", ascending=False).head(10)
        county_hist = px.histogram(
            county_summary,
            x="avg_demand_gw",
            nbins=50,
            color_discrete_sequence=["#0f766e"],
            title="Distribution of average county demand",
        )
        county_hist.update_traces(marker_line_width=0)
        county_hist.update_layout(template="plotly_white", margin=dict(l=40, r=20, t=60, b=40), height=360, xaxis_title="Average demand (GW)", yaxis_title="Number of counties")

        left, right = st.columns(2)
        with left:
            chart_definition("Top counties: the counties with the highest average electricity demand.")
            st.plotly_chart(
                top_counties_bar(
                    county_top.assign(avg_demand_gw=county_top["avg_demand_gw"]),
                    title="Top 10 counties by average demand",
                ),
                use_container_width=True,
            )
        with right:
            chart_definition("County distribution: how average demand is spread across all counties.")
            st.plotly_chart(county_hist, use_container_width=True)

        chart_definition("County map: average electricity demand by county across the U.S.")
        st.plotly_chart(
            county_choropleth(
                county_summary,
                geojson=counties_geojson,
                title="Average electricity demand by county",
                color_col="avg_demand_gw",
                color_bar_title="GW",
            ),
            use_container_width=True,
        )

        state_left, state_right = st.columns(2)
        with state_left:
            chart_definition("State map: average electricity demand by state.")
            st.plotly_chart(
                state_choropleth(
                    state_summary,
                    color_col="avg_demand_gw",
                    title="Average electricity demand by state",
                    color_bar_title="GW",
                ),
                use_container_width=True,
            )
        with state_right:
            chart_definition("Per-capita state map: average demand normalized by population.")
            st.plotly_chart(
                state_choropleth(
                    state_summary,
                    color_col="demand_per_100k_gw",
                    title="Demand per 100k residents by state",
                    color_bar_title="GW / 100k people",
                ),
                use_container_width=True,
            )

        state_rank = state_summary.sort_values("demand_per_100k_gw", ascending=False)[["state", "demand_per_100k_gw", "avg_demand_gw"]].head(10)
        st.dataframe(
            state_rank.rename(
                columns={
                    "state": "State",
                    "demand_per_100k_gw": "Demand / 100k people (GW)",
                    "avg_demand_gw": "Average demand (GW)",
                }
            ),
            use_container_width=True,
            height=280,
        )


# ---------------------------------------------------------------------------
# 8. Cross-country
# ---------------------------------------------------------------------------
with st.container(border=True):
    section_header(
        8,
        "Cross-country context",
        "A wider comparison focused on electricity per capita and GDP per capita.",
    )

    try:
        country_energy = get_country_energy()
    except FileNotFoundError as e:
        st.warning(str(e))
    else:
        country_frame = country_comparison_frame(country_energy)
        available_countries = sorted(country_frame["country"].dropna().unique().tolist())
        default_countries = [country for country in ["United States", "Canada", "China", "India"] if country in available_countries]

        selected_countries = st.multiselect(
            "Countries",
            options=available_countries,
            default=default_countries,
            key="country_compare",
            help="Choose a few countries to compare over time and in the GDP scatter.",
        )
        countries_for_plot = selected_countries or default_countries or available_countries[:4]
        country_subset = country_frame[country_frame["country"].isin(countries_for_plot)].copy()
        trend_latest_year = int(country_subset["year"].max())
        latest_complete = country_subset.dropna(subset=["gdp_per_capita_usd", "electricity_per_capita_kwh"]).copy()
        scatter_year = int(latest_complete["year"].max()) if not latest_complete.empty else trend_latest_year
        latest_subset = latest_complete[latest_complete["year"] == scatter_year].copy()
        if latest_subset.empty:
            latest_subset = country_subset[country_subset["year"] == scatter_year].copy()
        latest_subset = latest_subset.dropna(subset=["gdp_per_capita_usd", "electricity_per_capita_kwh"])

        left, right = st.columns(2)
        with left:
            chart_definition("Country trend: electricity use per person over time for the selected countries.")
            st.plotly_chart(
                country_trend(
                    country_subset,
                    countries=countries_for_plot,
                    title="Electricity use per capita over time",
                ),
                use_container_width=True,
            )
        with right:
            chart_definition("GDP vs electricity: each point is a country in the latest year with complete GDP and electricity data.")
            if latest_subset.empty:
                st.info("No country has complete GDP and electricity data for the selected set in the latest year.")
            else:
                st.plotly_chart(
                    country_scatter(
                        latest_subset,
                        title=f"GDP per capita vs electricity per capita ({scatter_year})",
                    ),
                    use_container_width=True,
                )

        country_metrics = st.columns(3)
        country_metrics[0].metric("Countries selected", len(countries_for_plot))
        country_metrics[1].metric("Trend data through", trend_latest_year)
        country_metrics[2].metric("Scatter year", scatter_year)
