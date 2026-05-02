"""Forecasting page for daily electricity load.

The model is intentionally stronger than a simple moving average but still
explainable for the final project: gradient boosting with trend, weekday,
annual seasonality, lag, and rolling-window features.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from sklearn.ensemble import HistGradientBoostingRegressor

from powerpulse.data import date_range, get_state_hourly, list_states


STATE_NAMES = {
    "AL": "Alabama",
    "AK": "Alaska",
    "AZ": "Arizona",
    "AR": "Arkansas",
    "CA": "California",
    "CO": "Colorado",
    "CT": "Connecticut",
    "DE": "Delaware",
    "FL": "Florida",
    "GA": "Georgia",
    "HI": "Hawaii",
    "ID": "Idaho",
    "IL": "Illinois",
    "IN": "Indiana",
    "IA": "Iowa",
    "KS": "Kansas",
    "KY": "Kentucky",
    "LA": "Louisiana",
    "ME": "Maine",
    "MD": "Maryland",
    "MA": "Massachusetts",
    "MI": "Michigan",
    "MN": "Minnesota",
    "MS": "Mississippi",
    "MO": "Missouri",
    "MT": "Montana",
    "NE": "Nebraska",
    "NV": "Nevada",
    "NH": "New Hampshire",
    "NJ": "New Jersey",
    "NM": "New Mexico",
    "NY": "New York",
    "NC": "North Carolina",
    "ND": "North Dakota",
    "OH": "Ohio",
    "OK": "Oklahoma",
    "OR": "Oregon",
    "PA": "Pennsylvania",
    "RI": "Rhode Island",
    "SC": "South Carolina",
    "SD": "South Dakota",
    "TN": "Tennessee",
    "TX": "Texas",
    "UT": "Utah",
    "VT": "Vermont",
    "VA": "Virginia",
    "WA": "Washington",
    "WV": "West Virginia",
    "WI": "Wisconsin",
    "WY": "Wyoming",
}
LAGS = (1, 2, 7, 14, 28)
ROLLING_WINDOWS = (7, 14)
FOURIER_ORDER = 4


@dataclass
class BoostedLoadModel:
    model: HistGradientBoostingRegressor
    feature_names: list[str]
    start_date: pd.Timestamp
    residual_std: float


def _daily_load_series(state_hourly: pd.DataFrame, state_code: str | None) -> pd.Series:
    hourly = state_hourly.sum(axis=1) if state_code is None else state_hourly[state_code]
    daily = hourly.resample("D").mean() / 1e3
    daily.name = "load_gw"
    daily.index.name = "date"
    return daily.asfreq("D").interpolate("time")


def _calendar_features(dates: pd.DatetimeIndex, start_date: pd.Timestamp) -> pd.DataFrame:
    days = (dates - start_date).days.to_numpy(dtype=float)
    day_of_year = dates.dayofyear.to_numpy(dtype=float)
    frame = pd.DataFrame(index=dates)
    frame["trend"] = days / 365.25
    frame["trend_sq"] = frame["trend"] ** 2
    for weekday in range(1, 7):
        frame[f"weekday_{weekday}"] = (dates.dayofweek == weekday).astype(float)
    for order in range(1, FOURIER_ORDER + 1):
        angle = 2 * np.pi * order * day_of_year / 365.25
        frame[f"annual_sin_{order}"] = np.sin(angle)
        frame[f"annual_cos_{order}"] = np.cos(angle)
    return frame


def _lag_features(values: pd.Series, dates: pd.DatetimeIndex, use_actual_for_target_day: bool) -> pd.DataFrame:
    history = values.copy()
    if not use_actual_for_target_day:
        history = history.reindex(history.index.union(dates)).sort_index()
    frame = pd.DataFrame(index=dates)
    for lag in LAGS:
        shifted = history.shift(lag).reindex(dates)
        frame[f"lag_{lag}"] = shifted
    for window in ROLLING_WINDOWS:
        rolled = history.shift(1).rolling(window).mean().reindex(dates)
        frame[f"roll_{window}"] = rolled
    return frame


def _feature_frame(values: pd.Series, dates: pd.DatetimeIndex, start_date: pd.Timestamp, actual_lags: bool) -> pd.DataFrame:
    return pd.concat(
        [
            _calendar_features(dates, start_date),
            _lag_features(values, dates, use_actual_for_target_day=actual_lags),
        ],
        axis=1,
    )


def _fit_boosted_model(series: pd.Series, train_end: pd.Timestamp) -> BoostedLoadModel:
    train = series.loc[:train_end]
    features = _feature_frame(train, train.index, train.index.min(), actual_lags=True)
    frame = features.join(train.rename("target")).dropna()
    x_raw = frame.drop(columns=["target"])
    y = frame["target"].to_numpy(dtype=float)

    model = HistGradientBoostingRegressor(
        loss="squared_error",
        learning_rate=0.045,
        max_iter=350,
        max_leaf_nodes=31,
        l2_regularization=0.08,
        random_state=42,
    )
    model.fit(x_raw, y)
    fitted = model.predict(x_raw)
    residual_std = float(np.std(y - fitted, ddof=min(1, len(y) - 1)))
    return BoostedLoadModel(
        model=model,
        feature_names=x_raw.columns.tolist(),
        start_date=train.index.min(),
        residual_std=residual_std,
    )


def _predict(model: BoostedLoadModel, features: pd.DataFrame) -> pd.Series:
    x = features[model.feature_names].copy()
    x = x.ffill().bfill()
    return pd.Series(model.model.predict(x), index=features.index, name="Gradient boosting")


def _boosted_walk_forward(series: pd.Series, train_end: pd.Timestamp, test_index: pd.DatetimeIndex) -> pd.Series:
    model = _fit_boosted_model(series, train_end)
    features = _feature_frame(series, test_index, model.start_date, actual_lags=True)
    return _predict(model, features)


def _boosted_future(series: pd.Series, horizon: int) -> tuple[pd.Series, float]:
    model = _fit_boosted_model(series, series.index[-1])
    future_index = pd.date_range(series.index[-1] + pd.Timedelta(days=1), periods=horizon, freq="D", tz=series.index.tz)
    extended = series.copy()
    preds: list[float] = []
    for date in future_index:
        features = _feature_frame(extended, pd.DatetimeIndex([date]), model.start_date, actual_lags=False)
        pred = float(_predict(model, features).iloc[0])
        preds.append(pred)
        extended.loc[date] = pred
    return pd.Series(preds, index=future_index, name="Gradient boosting"), model.residual_std


def _seasonal_naive(history: pd.Series, dates: pd.DatetimeIndex, lag: int = 7) -> pd.Series:
    pred = history.shift(lag).reindex(dates)
    return pred.ffill().rename("Weekly naive")


def _rolling_mean(history: pd.Series, dates: pd.DatetimeIndex, window: int = 7) -> pd.Series:
    pred = history.shift(1).rolling(window).mean().reindex(dates)
    return pred.ffill().rename("Rolling mean")


def _future_baseline(history: pd.Series, horizon: int, method: str) -> pd.Series:
    values = history.to_numpy(dtype=float).tolist()
    preds: list[float] = []
    for _ in range(horizon):
        if method == "Weekly naive":
            pred = values[-7]
        else:
            pred = float(np.mean(values[-7:]))
        preds.append(float(pred))
        values.append(float(pred))
    index = pd.date_range(history.index[-1] + pd.Timedelta(days=1), periods=horizon, freq="D", tz=history.index.tz)
    return pd.Series(preds, index=index, name=method)


def _mape(actual: pd.Series, forecast: pd.Series) -> float:
    denom = actual.abs().replace(0, np.nan)
    return float(((actual - forecast).abs() / denom).mean() * 100)


def _evaluate(series: pd.Series, holdout_year: int = 2023) -> tuple[pd.DataFrame, pd.DataFrame]:
    tz = series.index.tz
    train_end = pd.Timestamp(f"{holdout_year - 1}-12-31", tz=tz)
    test_start = pd.Timestamp(f"{holdout_year}-01-01", tz=tz)
    test_end = pd.Timestamp(f"{holdout_year}-12-31", tz=tz)
    test = series.loc[test_start:test_end]
    forecasts = {
        "Gradient boosting": _boosted_walk_forward(series, train_end, test.index),
        "Weekly naive": _seasonal_naive(series, test.index),
        "Rolling mean": _rolling_mean(series, test.index),
    }

    scores = []
    holdout = pd.DataFrame({"Observed": test})
    for name, pred in forecasts.items():
        aligned = pred.reindex(test.index)
        holdout[name] = aligned
        scores.append(
            {
                "method": name,
                "MAPE": _mape(test, aligned),
                "MAE": float((test - aligned).abs().mean()),
            }
        )
    return pd.DataFrame(scores).sort_values("MAPE").reset_index(drop=True), holdout


def _holdout_figure(frame: pd.DataFrame, region: str) -> go.Figure:
    fig = go.Figure()
    colors = {
        "Observed": "#111827",
        "Gradient boosting": "#2563eb",
        "Weekly naive": "#64748b",
        "Rolling mean": "#c2410c",
    }
    for col in frame.columns:
        fig.add_trace(
            go.Scatter(
                x=frame.index,
                y=frame[col],
                mode="lines",
                name=col,
                line=dict(color=colors[col], width=2.7 if col in ("Observed", "Gradient boosting") else 1.8, dash="solid" if col in ("Observed", "Gradient boosting") else "dash"),
            )
        )
    fig.update_layout(
        template="plotly_white",
        title=f"{region}: 2023 daily load backtest",
        xaxis_title="Date",
        yaxis_title="Daily average load (GW)",
        margin=dict(l=40, r=20, t=70, b=40),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.03, xanchor="right", x=1),
        height=430,
    )
    return fig


def _future_figure(history: pd.Series, forecast: pd.Series, residual_std: float, region: str) -> go.Figure:
    recent_window = max(180, min(365, len(forecast) * 2))
    recent = history.loc[history.index >= history.index[-1] - pd.Timedelta(days=recent_window)]
    upper = forecast + 1.28 * residual_std
    lower = forecast - 1.28 * residual_std
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=recent.index, y=recent, mode="lines", name="Observed", line=dict(color="#111827", width=2.4)))
    fig.add_trace(go.Scatter(x=upper.index, y=upper, mode="lines", name="Upper band", line=dict(width=0), showlegend=False))
    fig.add_trace(
        go.Scatter(
            x=lower.index,
            y=lower,
            mode="lines",
            name="Forecast band",
            fill="tonexty",
            fillcolor="rgba(37, 99, 235, 0.16)",
            line=dict(width=0),
        )
    )
    fig.add_trace(go.Scatter(x=forecast.index, y=forecast, mode="lines+markers", name="Gradient boosting forecast", line=dict(color="#2563eb", width=3)))
    fig.add_vline(x=history.index[-1], line_width=1, line_dash="dot", line_color="#94a3b8")
    fig.update_layout(
        template="plotly_white",
        title=f"{region}: next days forecast",
        xaxis_title="Date",
        yaxis_title="Daily average load (GW)",
        margin=dict(l=40, r=20, t=70, b=40),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.03, xanchor="right", x=1),
        height=430,
    )
    return fig


st.markdown(
    """
    <style>
    .block-container { padding-top: 1.1rem; padding-bottom: 2rem; }
    .pp-hero {
        background: linear-gradient(135deg, #10231f 0%, #17463d 52%, #24313b 100%);
        color: white;
        border-radius: 18px;
        padding: 1.35rem 1.45rem 1.2rem 1.45rem;
        margin-bottom: 1rem;
        box-shadow: 0 14px 34px rgba(15, 23, 42, 0.16);
    }
    .pp-hero h1 { margin: 0; font-size: 2.15rem; line-height: 1.08; }
    .pp-hero p { margin-top: 0.55rem; margin-bottom: 0; max-width: 76ch; color: rgba(255,255,255,0.88); }
    .pp-kicker {
        font-size: 0.72rem; font-weight: 800; letter-spacing: 0.17em;
        text-transform: uppercase; color: #99f6e4; margin-bottom: 0.4rem;
    }
    .pp-section-tag { font-size: 0.72rem; font-weight: 800; letter-spacing: 0.15em; text-transform: uppercase; color: #0f766e; }
    .pp-section-title { font-size: 1.35rem; font-weight: 800; color: #0f172a; margin-bottom: 0.1rem; }
    .pp-section-note { color: #64748b; font-size: 0.95rem; margin-bottom: 0.55rem; }
    .pp-metric-grid {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 0.7rem;
        margin: 0.25rem 0 1rem 0;
    }
    .pp-metric {
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 0.75rem 0.85rem;
        background: #ffffff;
    }
    .pp-metric-label {
        color: #64748b;
        font-size: 0.78rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        margin-bottom: 0.28rem;
    }
    .pp-metric-value {
        color: #0f172a;
        font-size: clamp(1.1rem, 1.8vw, 1.55rem);
        font-weight: 800;
        line-height: 1.15;
        overflow-wrap: anywhere;
    }
    @media (max-width: 900px) {
        .pp-metric-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def section_header(title: str, note: str) -> None:
    st.markdown(
        f"""
        <div class="pp-section-tag">Forecast module</div>
        <div class="pp-section-title">{title}</div>
        <div class="pp-section-note">{note}</div>
        """,
        unsafe_allow_html=True,
    )


st.markdown(
    """
    <div class="pp-hero">
      <div class="pp-kicker">PowerPulse</div>
      <h1>Daily Load Forecasting</h1>
      <p>
        Forecast daily average electricity load for a small set of regions using
        gradient boosting with trend, weekday, annual seasonality, and recent-load features.
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)

try:
    state_hourly = get_state_hourly()
except FileNotFoundError as e:
    st.error(str(e))
    st.stop()

start, end = date_range()
state_options = list_states()
region_options = ["National"] + state_options

with st.sidebar:
    st.subheader("Forecast controls")
    region = st.selectbox(
        "Region",
        options=region_options,
        index=0,
        format_func=lambda value: "National" if value == "National" else f"{STATE_NAMES.get(value, value)} ({value})",
    )
    horizon = st.slider("Forecast horizon (days)", min_value=7, max_value=180, value=30, step=7)
    st.caption(f"Historical coverage: {start.date()} to {end.date()}")

state_code = None if region == "National" else region
region_label = "National" if region == "National" else f"{STATE_NAMES.get(region, region)} ({region})"
series = _daily_load_series(state_hourly, state_code)
scores, holdout_frame = _evaluate(series)
future_forecast, residual_std = _boosted_future(series, horizon)
best_method = scores.loc[0, "method"]

st.markdown(
    f"""
    <div class="pp-metric-grid">
      <div class="pp-metric"><div class="pp-metric-label">Region</div><div class="pp-metric-value">{region_label}</div></div>
      <div class="pp-metric"><div class="pp-metric-label">Target</div><div class="pp-metric-value">Daily avg load</div></div>
      <div class="pp-metric"><div class="pp-metric-label">Best method</div><div class="pp-metric-value">{best_method}</div></div>
      <div class="pp-metric"><div class="pp-metric-label">Best MAPE</div><div class="pp-metric-value">{scores.loc[0, 'MAPE']:.1f}%</div></div>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.container(border=True):
    section_header(
        "Backtest comparison",
        "The model is trained through 2022 and tested against observed daily load in 2023.",
    )
    left, right = st.columns([0.9, 1.4])
    with left:
        st.caption("MAPE and MAE compare predicted daily average load against observed 2023 values; lower is better.")
        st.dataframe(scores.style.format({"MAPE": "{:.1f}%", "MAE": "{:.2f}"}), width='stretch', hide_index=True)
        st.caption("Gradient boosting features: trend, weekday dummies, annual Fourier seasonality, lags 1/2/7/14/28, and 7/14-day rolling means.")
    with right:
        st.caption("Black is observed 2023 daily load; blue is gradient boosting; dashed lines are baseline methods.")
        st.plotly_chart(_holdout_figure(holdout_frame, region_label), width='stretch')

with st.container(border=True):
    section_header(
        "Forward forecast",
        "The gradient boosting model is refit through the latest available day and projected forward recursively.",
    )
    st.caption("The shaded band is a simple residual-based uncertainty range, not an operational reliability interval.")
    st.plotly_chart(_future_figure(series, future_forecast, residual_std, region_label), width='stretch')
