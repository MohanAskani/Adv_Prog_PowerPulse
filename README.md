# PowerPulse

Streamlit web app for exploring U.S. electricity demand, grid stress, renewable mismatch, and short-term forecasting.

Course: **Rutgers Advanced Programming, Spring 2026**
Team **Debuggers**: Mohan Askani, Pranshu Verma, Neel Barve

## Module ownership

| Module | Owner | Status |
|---|---|---|
| Overview | Pranshu | stub |
| Demand Explorer | Mohan | in progress |
| Grid Stress | Mohan | stub |
| Renewable Mismatch | Neel | stub |
| Forecasting | (held) | stub |

## Architecture

The app **never reads the raw 1.7 GB HDF5 file at runtime**. A one-time ETL (`scripts/build_aggregates.py`) reads `historic_load_hourly_2016_2023_county.h5`, joins counties to states via `national_county.txt`, and emits Parquet aggregates under `data/aggregates/`. Pages load only those Parquets, gated through `@st.cache_data` in `powerpulse/data.py`. This is the only way to keep page interactions snappy.

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
│   └── aggregates/              # baked parquets (git-ignored if large)
├── requirements.txt
└── .streamlit/config.toml
```

## Setup

```bash
# from this directory (powerpulse/)
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# one-time: build aggregates from the h5 file (sits one level up)
python scripts/build_aggregates.py

# run the app
streamlit run app.py
```

## Notes for the team

- **Timestamps are UTC** in the source h5. The Demand Explorer currently uses UTC hour-of-day; converting to local time per state is on the backlog.
- The midterm code dropped Autauga County (`p01001`) by mistake (`df.iloc[:, 1:]` on an index-only DataFrame). The ETL here uses **all 3,109 counties** so national totals will differ slightly from the midterm report.
- All chart functions live in `powerpulse/viz.py` so the four pages share a consistent style.
