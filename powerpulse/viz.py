"""Reusable Plotly chart helpers.

Pages should call these instead of building Plotly figures inline. Keeping
chart construction here ensures the four modules share a consistent look
(axis titles, hover formatting, color palette) and lets us tune the visual
language in one place before submission.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


# Shared style. Plotly's default color cycle is fine; we override only the
# template and a few axis defaults so charts look at home in Streamlit.
_TEMPLATE = "plotly_white"


def _apply_common_layout(
    fig: go.Figure,
    title: str,
    y_title: str,
    x_title: str,
    height: int | None = None,
) -> go.Figure:
    fig.update_layout(
        template=_TEMPLATE,
        title=title,
        xaxis_title=x_title,
        yaxis_title=y_title,
        margin=dict(l=40, r=20, t=60, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
    )
    if height is not None:
        fig.update_layout(height=height)
    return fig


def hour_of_day_total(
    series_mw: pd.Series,
    title: str = "Average demand by hour of day (UTC)",
) -> go.Figure:
    """Single-line chart of aggregate demand by hour, MW -> GW for readability."""
    gw = series_mw / 1000.0
    fig = go.Figure(
        go.Scatter(
            x=gw.index,
            y=gw.values,
            mode="lines+markers",
            name="Aggregate demand",
            hovertemplate="Hour %{x:02d}:00 UTC<br>%{y:.1f} GW<extra></extra>",
        )
    )
    fig.update_xaxes(tickmode="linear", tick0=0, dtick=2)
    return _apply_common_layout(fig, title, "Average demand (GW)", "Hour of day (UTC)")


def hour_of_day_by_state(
    df_mw: pd.DataFrame,
    title: str = "Average demand by hour of day, per state (UTC)",
) -> go.Figure:
    """Multi-line chart with one trace per state column. Values shown in GW."""
    gw = df_mw / 1000.0
    fig = go.Figure()
    for state in gw.columns:
        fig.add_trace(
            go.Scatter(
                x=gw.index,
                y=gw[state].values,
                mode="lines+markers",
                name=state,
                hovertemplate=f"{state} %{{x:02d}}:00 UTC<br>%{{y:.2f}} GW<extra></extra>",
            )
        )
    fig.update_xaxes(tickmode="linear", tick0=0, dtick=2)
    return _apply_common_layout(fig, title, "Average demand (GW)", "Hour of day (UTC)")


def yearly_energy_trend(series_twh: pd.Series, title: str) -> go.Figure:
    fig = go.Figure(
        go.Scatter(
            x=series_twh.index,
            y=series_twh.values,
            mode="lines+markers",
            line=dict(width=3, color="#0f766e"),
            marker=dict(size=9),
            hovertemplate="%{x}<br>%{y:.1f} TWh<extra></extra>",
            name="Annual energy",
        )
    )
    fig.update_xaxes(tickmode="linear", dtick=1)
    return _apply_common_layout(fig, title, "Annual energy (TWh)", "Year", height=360)


def yearly_boxplot(frame: pd.DataFrame, title: str) -> go.Figure:
    fig = px.box(
        frame,
        x="year",
        y="demand_gw",
        points="outliers",
    )
    fig.update_traces(marker=dict(size=4, color="#0f766e"), line=dict(width=1.5, color="#0f766e"))
    fig.update_xaxes(type="category")
    return _apply_common_layout(fig, title, "Hourly demand (GW)", "Year", height=360)


def weekday_weekend_lines(frame: pd.DataFrame, title: str) -> go.Figure:
    pivot = frame.pivot(index="hour_utc", columns="day_type", values="demand_gw").reindex(columns=["Weekday", "Weekend"])
    fig = go.Figure()
    palette = {"Weekday": "#0f766e", "Weekend": "#f97316"}
    for name in pivot.columns:
        fig.add_trace(
            go.Scatter(
                x=pivot.index,
                y=pivot[name],
                mode="lines+markers",
                name=name,
                line=dict(width=3, color=palette.get(name)),
                marker=dict(size=7),
                hovertemplate=f"{name} %{{x:02d}}:00 UTC<br>%{{y:.1f}} GW<extra></extra>",
            )
        )
    fig.update_xaxes(tickmode="linear", tick0=0, dtick=2)
    return _apply_common_layout(fig, title, "Average demand (GW)", "Hour of day (UTC)", height=360)


def weekday_weekend_gap(frame: pd.DataFrame, title: str) -> go.Figure:
    pivot = frame.pivot(index="hour_utc", columns="day_type", values="demand_gw").reindex(columns=["Weekday", "Weekend"])
    gap = pivot["Weekday"] - pivot["Weekend"]
    fig = go.Figure(
        go.Bar(
            x=gap.index,
            y=gap.values,
            marker_color="#2563eb",
            hovertemplate="Hour %{x:02d}:00 UTC<br>Gap %{y:.1f} GW<extra></extra>",
            name="Weekday minus weekend",
        )
    )
    fig.update_xaxes(tickmode="linear", tick0=0, dtick=2)
    return _apply_common_layout(fig, title, "Demand gap (GW)", "Hour of day (UTC)", height=360)


def monthly_trend(series: pd.Series, title: str) -> go.Figure:
    month_labels = {1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun", 7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"}
    x = [month_labels[m] for m in series.index]
    fig = go.Figure(
        go.Scatter(
            x=x,
            y=series.values,
            mode="lines+markers",
            line=dict(width=3, color="#7c3aed"),
            marker=dict(size=9),
            hovertemplate="%{x}<br>%{y:.1f} GW<extra></extra>",
            name="Monthly average",
        )
    )
    return _apply_common_layout(fig, title, "Average demand (GW)", "Month", height=360)


def seasonal_bar(series: pd.Series, title: str) -> go.Figure:
    fig = go.Figure(
        go.Bar(
            x=series.index.tolist(),
            y=series.values,
            marker_color=["#0f766e", "#22c55e", "#f97316", "#2563eb"],
            hovertemplate="%{x}<br>%{y:.1f} GW<extra></extra>",
            name="Seasonal average",
        )
    )
    return _apply_common_layout(fig, title, "Average demand (GW)", "Season", height=360)


def month_hour_heatmap(pivot: pd.DataFrame, title: str) -> go.Figure:
    month_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    fig = go.Figure(
        go.Heatmap(
            z=pivot.values,
            x=[f"{hour:02d}" for hour in pivot.columns],
            y=month_labels,
            colorscale="Viridis",
            colorbar=dict(title="GW"),
            hovertemplate="Month %{y}<br>Hour %{x}:00 UTC<br>%{z:.1f} GW<extra></extra>",
        )
    )
    return _apply_common_layout(fig, title, "Month", "Hour of day (UTC)", height=440)


def month_boxplot(frame: pd.DataFrame, title: str) -> go.Figure:
    fig = px.box(
        frame,
        x="month_name",
        y="demand_gw",
        points=False,
    )
    fig.update_traces(line=dict(width=1.2, color="#7c3aed"), marker=dict(color="#7c3aed"))
    return _apply_common_layout(fig, title, "Hourly demand (GW)", "Month", height=360)


def yearly_volatility(series: pd.Series, title: str) -> go.Figure:
    fig = go.Figure(
        go.Bar(
            x=series.index,
            y=series.values,
            marker_color="#1d4ed8",
            hovertemplate="%{x}<br>Std dev %{y:.1f} GW<extra></extra>",
            name="Volatility",
        )
    )
    fig.update_xaxes(tickmode="linear", dtick=1)
    return _apply_common_layout(fig, title, "Std dev (GW)", "Year", height=360)


def yearly_peak_line(series: pd.Series, title: str) -> go.Figure:
    fig = go.Figure(
        go.Scatter(
            x=series.index,
            y=series.values,
            mode="lines+markers",
            line=dict(width=3, color="#b45309"),
            marker=dict(size=9),
            hovertemplate="%{x}<br>Peak %{y:.1f} GW<extra></extra>",
            name="Annual peak",
        )
    )
    fig.update_xaxes(tickmode="linear", dtick=1)
    return _apply_common_layout(fig, title, "Peak demand (GW)", "Year", height=360)


def top_counties_bar(frame: pd.DataFrame, title: str) -> go.Figure:
    top = frame.sort_values("avg_demand_mw", ascending=True)
    fig = go.Figure(
        go.Bar(
            x=top["avg_demand_gw"],
            y=top["county_label"],
            orientation="h",
            marker_color="#0f766e",
            hovertemplate="%{y}<br>%{x:.1f} GW<extra></extra>",
            name="County demand",
        )
    )
    return _apply_common_layout(fig, title, "County", "Average demand (GW)", height=400)


def state_choropleth(frame: pd.DataFrame, color_col: str, title: str, color_bar_title: str) -> go.Figure:
    fig = px.choropleth(
        frame,
        locations="state",
        locationmode="USA-states",
        color=color_col,
        scope="usa",
        color_continuous_scale="Viridis",
        title=title,
    )
    fig.update_traces(colorbar_title_text=color_bar_title)
    return _apply_common_layout(fig, title, color_bar_title, "State", height=430)


def county_choropleth(frame: pd.DataFrame, geojson: dict, title: str, color_col: str, color_bar_title: str) -> go.Figure:
    fig = px.choropleth(
        frame,
        geojson=geojson,
        locations="fips",
        color=color_col,
        color_continuous_scale="Viridis",
        scope="usa",
        title=title,
    )
    fig.update_traces(colorbar_title_text=color_bar_title, marker_line_color="white", marker_line_width=0.25)
    fig.update_geos(fitbounds="locations", visible=False)
    return _apply_common_layout(fig, title, color_bar_title, "County", height=430)


def country_trend(frame: pd.DataFrame, countries: list[str], title: str) -> go.Figure:
    subset = frame[frame["country"].isin(countries)].copy()
    fig = px.line(
        subset,
        x="year",
        y="electricity_per_capita_kwh",
        color="country",
        markers=True,
        title=title,
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig.update_traces(hovertemplate="%{fullData.name}<br>%{x}<br>%{y:.0f} kWh per person<extra></extra>")
    fig.update_xaxes(tickmode="linear", dtick=1)
    fig = _apply_common_layout(fig, title, "Electricity per capita (kWh)", "Year", height=380)
    fig.update_layout(
        title=dict(text=title, x=0.02, xanchor="left"),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.24,
            xanchor="left",
            x=0,
        ),
        margin=dict(l=40, r=20, t=80, b=100),
    )
    return fig


def country_scatter(frame: pd.DataFrame, title: str) -> go.Figure:
    fig = px.scatter(
        frame,
        x="gdp_per_capita_usd",
        y="electricity_per_capita_kwh",
        text="country",
        hover_name="country",
        size="population",
        size_max=28,
        color_discrete_sequence=["#0f766e"],
        title=title,
    )
    fig.update_traces(textposition="top center", marker=dict(line=dict(width=0.5, color="white")))
    fig.update_xaxes(tickformat="$,.0f")
    return _apply_common_layout(fig, title, "Electricity per capita (kWh)", "GDP per capita (USD)", height=430)
