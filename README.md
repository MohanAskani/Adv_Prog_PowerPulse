# PowerPulse

Streamlit web app for exploring U.S. electricity demand, grid stress, renewable mismatch, and short-term forecasting.

Course: **Rutgers Advanced Programming, Spring 2026**
Team **Debuggers**: Mohan Askani, Pranshu Verma, Neel Barve

## Module ownership

| Module | Owner | Status |
|---|---|---|
| Overview | Mohan | stub |
| Demand Explorer | Mohan | in progress |
| Grid Stress | Neel | stub |
| Renewable Mismatch | Pranshu | stub |
| Forecasting | Mohan | in progress |

## Architecture

The app **never reads the raw 1.7 GB HDF5 file at runtime**. A one-time ETL (`scripts/build_aggregates.py`) reads `historic_load_hourly_2016_2023_county.h5`, joins counties to states via `national_county.txt`, and emits Parquet aggregates under `data/aggregates/`. Pages load only those Parquets, gated through `@st.cache_data` in `powerpulse/data.py`. This keeps page interactions snappy.

```
powerpulse/
├── app.py                       # entry; declares st.navigation pages
├── pages/                       # one file per module
├── powerpulse/                  # importable package
│   ├── data.py                  # cached parquet loaders
│   ├── transforms.py            # rollups, peak detection, per-capita
│   ├── stress.py                # grid stress score (Mohan)
│   ├── mismatch.py              # renewable mismatch metrics (Neel)
│   └── viz.py                   # shared plotly chart helpers
├── scripts/
│   └── build_aggregates.py      # one-time ETL: h5 → parquet
├── data/
│   └── aggregates/              # baked parquets committed for easy setup
│   └── external/                # small shared files needed in cloud deploys
├── requirements.txt
└── .streamlit/config.toml
```

## Setup

```bash
# from this directory (repo root)
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# run the app with the committed aggregate data
streamlit run app.py
```

The app should open at `http://localhost:8501`. The committed files under `data/aggregates/` and `data/external/` are enough for the Overview, Demand Explorer, and Forecasting pages to run after cloning or on Streamlit Community Cloud.

## Rebuild Aggregates

Only rebuild aggregates if the raw demand or population source files change.

```bash
# expected next to the repo root:
# - historic_load_hourly_2016_2023_county.h5
# - co-est2024-pop.xlsx
# - owid-energy-datav2.csv
# - counties.geojson
python scripts/build_aggregates.py
```

## Local Run

If you already have a virtual environment, you can reuse it:

```bash
source .venv/bin/activate
.venv/bin/python -m streamlit run app.py
```

## Notes for the team

- **Timestamps are UTC** in the source h5. The Demand Explorer currently uses UTC hour-of-day; converting to local time per state is on the backlog.
- The midterm code dropped Autauga County (`p01001`) by mistake (`df.iloc[:, 1:]` on an index-only DataFrame). The ETL here uses **all 3,109 counties** so national totals will differ slightly from the midterm report.
- All chart functions live in `powerpulse/viz.py` so the four pages share a consistent style.
- The committed parquet files under `data/aggregates/` let teammates run the app immediately after cloning; regenerate them with `python scripts/build_aggregates.py` if the source data changes.
- Forecasting uses `scikit-learn` gradient boosting with daily average load, calendar seasonality, lag features, and a 2023 backtest against simple baselines.
