"""Reusable Plotly chart helpers.

Pages should call these instead of building Plotly figures inline. Keeping
chart construction here ensures the four modules share a consistent look
(axis titles, hover formatting, color palette) and lets us tune the visual
language in one place before submission.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go


# Shared style. Plotly's default color cycle is fine; we override only the
# template and a few axis defaults so charts look at home in Streamlit.
_TEMPLATE = "plotly_white"


def _apply_common_layout(fig: go.Figure, title: str, y_title: str, x_title: str) -> go.Figure:
    fig.update_layout(
        template=_TEMPLATE,
        title=title,
        xaxis_title=x_title,
        yaxis_title=y_title,
        margin=dict(l=40, r=20, t=60, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
    )
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
