# PowerPulse

Streamlit web app for explaining why electricity demand matters, exploring U.S. load patterns, scoring grid stress, measuring renewable mismatch, and forecasting short-term demand.

Course: **Rutgers Advanced Programming, Spring 2026**
Team **Debuggers**: Mohan Askani, Pranshu Verma, Neel Barve

## Module ownership

| Module | Owner | Status |
|---|---|---|
| Why PowerPulse | Team Debuggers | complete |
| Demand Explorer | Mohan | complete |
| Grid Stress | Neel | complete |
| Renewable Mismatch | Pranshu | complete |
| Forecasting | Mohan | complete |

## Architecture

The app **never reads the raw 1.7 GB HDF5 file at runtime**. A one-time ETL (`scripts/build_aggregates.py`) reads `historic_load_hourly_2016_2023_county.h5`, joins counties to states via `national_county.txt`, and emits Parquet aggregates under `data/aggregates/`. Pages load only those Parquets, gated through `@st.cache_data` in `powerpulse/data.py`. This keeps page interactions snappy.

The Grid Stress page also uses `data/aggregates/generation_monthly.parquet`, a compact monthly state-level aggregate built from `monthly_gen_2001_24.xlsx`. It is used as supply context only; the stress score itself is demand-based.

```
powerpulse/
├── app.py                       # entry; declares st.navigation pages
├── pages/                       # one file per module
├── powerpulse/                  # importable package
│   ├── data.py                  # cached parquet loaders
│   ├── transforms.py            # rollups, peak detection, per-capita
│   ├── stress.py                # grid stress score and demand-pressure metrics
│   ├── mismatch.py              # renewable mismatch metrics
│   └── viz.py                   # shared plotly chart helpers
├── scripts/
│   ├── build_aggregates.py      # one-time ETL: h5 -> parquet
│   └── build_generation_monthly.py
├── data/
│   └── aggregates/              # baked parquets committed for easy setup
│   └── external/                # small shared files needed in cloud deploys
├── requirements.txt
└── .streamlit/config.toml
```

## Setup

```bash
# from this directory: Adv_Prog_PowerPulse
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# run the app with the committed aggregate data
streamlit run app.py
```

The app should open at `http://localhost:8501`. The committed files under `data/aggregates/`, `data/external/`, and the repo-root compatibility copies are enough for all active pages to run after cloning or on Streamlit Community Cloud.

## Streamlit Community Cloud

Use these settings when deploying from GitHub:

- Repository: `MohanAskani/Adv_Prog_PowerPulse`
- Branch: `master` after the final merge, or `Mohan` while testing team updates
- Main file path: `app.py`
- Python dependencies: installed from `requirements.txt`

No raw `.h5` file is needed for deployment because the app reads committed aggregate Parquet files.

## Rebuild Aggregates

Only rebuild aggregates if the raw demand or population source files change.

```bash
# expected next to the repo root:
# - historic_load_hourly_2016_2023_county.h5
# - co-est2024-pop.xlsx
# - owid-energy-datav2.csv
# - counties.geojson
python scripts/build_aggregates.py

# optional: rebuild monthly generation context
python scripts/build_generation_monthly.py
```

## Local Run

If you already have a virtual environment, you can reuse it:

```bash
source .venv/bin/activate
.venv/bin/python -m streamlit run app.py
```

## Notes for the team

- **Timestamps are UTC** in the source h5. The Demand Explorer currently uses UTC hour-of-day; converting to local time per state is a future improvement.
- Earlier notebook code dropped Autauga County (`p01001`) by mistake (`df.iloc[:, 1:]` on an index-only DataFrame). The ETL here uses **all 3,109 counties** so national totals may differ slightly from earlier reports.
- All chart functions live in `powerpulse/viz.py` so the four pages share a consistent style.
- The committed parquet files under `data/aggregates/` let teammates run the app immediately after cloning; regenerate them with `python scripts/build_aggregates.py` if the source data changes.
- Forecasting uses `scikit-learn` gradient boosting with daily average load, calendar seasonality, lag features, and a 2023 backtest against simple baselines.
- Grid Stress uses a transparent 0-100 score from hourly demand: peak intensity, volatility, seasonal extremes, ramp severity, and near-peak persistence. Monthly generation adds total/renewable/fossil context, but it is not treated as hourly reliability data.
