# Industrial Inventory Intelligence Platform

An ML-driven platform that forecasts component/material consumption for a
manufacturing plant, computes criticality- and variability-weighted reorder
points and EOQ, and cross-references machine health predictions to flag
maintenance-linked reorders before a stockout causes downtime.

## What it does

- **Demand Forecasting** — XGBoost model predicts component consumption 30 days
  ahead, based on historical usage, production cycles, and shift patterns.
- **Inventory Optimization** — Safety stock, reorder point, and EOQ calculated
  per component, with safety stock scaled by both demand variability AND
  machine criticality.
- **Machine Health Prediction** — A separate ML model trained on sensor data
  (temperature, torque, rotational speed, tool wear) predicts failure risk and
  projects when a machine will cross a critical threshold.
- **Maintenance-Linked Triggers** — If a machine is predicted to hit critical
  risk before its next scheduled maintenance, its linked components get
  auto-flagged for reorder — independent of demand-based logic.
- **Downtime Cost Calculator** — Every urgent alert shows an estimated ₹ cost
  of downtime if the stockout isn't addressed.

## Folder structure

```
industrial-inventory-platform/
├── data/
│   ├── raw/            (empty — place real Kaggle CSVs here if you swap in real data)
│   └── processed/       (generated datasets + model outputs, already populated)
├── src/
│   ├── data_generation.py   → builds the synthetic dataset
│   ├── forecasting.py       → XGBoost demand forecasting model
│   ├── inventory_logic.py   → EOQ / reorder point / safety stock / downtime cost
│   ├── maintenance.py       → ML machine health model + maintenance triggers
│   └── utils.py              → shared data-loading helpers for the app
├── pages/                    → Streamlit multi-page app
│   ├── 1_Demand_Forecasts.py
│   ├── 2_Reorder_Recommendations.py
│   ├── 3_Maintenance_Machine_Health.py
│   ├── 4_Maintenance_Calendar.py
│   └── 5_Alerts.py
├── Home.py                   → main entry page (Overview)
└── requirements.txt
```

## How to run it (step by step)

**1. Install dependencies** (from inside the project folder):
```bash
pip install -r requirements.txt --break-system-packages
```
(Drop `--break-system-packages` if you're using a virtual environment instead —
recommended: `python3 -m venv venv && source venv/bin/activate` first.)

**2. (Already done, but if you want to regenerate data/models):**
```bash
python3 src/data_generation.py     # regenerates all synthetic CSVs
python3 src/forecasting.py         # retrains the demand forecasting model
python3 src/inventory_logic.py     # recalculates reorder recommendations
python3 src/maintenance.py         # retrains the machine health model
```
Run these in this exact order if you regenerate — each one depends on the
previous step's output files in `data/processed/`.

**3. Launch the app:**
```bash
streamlit run Home.py
```
This opens the app in your browser at `http://localhost:8501`. Use the
sidebar to move between pages.

## Using real Kaggle data instead of synthetic data

If you download the real datasets later:
- **Store Item Demand Forecasting** (Kaggle) → maps to `consumption.csv`
  (columns: date, store→machine_id, item→component_id, sales→qty_consumed)
- **AI4I 2020 Predictive Maintenance Dataset** (Kaggle) → maps to
  `machine_health.csv` (sensor columns already match: air/process temperature,
  rotational speed, torque, tool wear)

Place the raw files in `data/raw/`, then adjust `src/data_generation.py` (or
write a small loader) to read from there instead of generating synthetic rows
— the rest of the pipeline (forecasting, inventory logic, maintenance model)
will work unchanged since the column names/schema already match.

## Model performance (on the current synthetic dataset)

- Demand forecasting (XGBoost): **MAE ≈ 2.6%** of average daily consumption
  (tested on the most recent 90 days, unseen during training)
- Failure risk model (XGBoost): **R² ≈ 0.95**, MAE ≈ 0.045 on a 0–1 risk scale

## Notes / assumptions used (good to know for your report or interview)

- Service level for safety stock: 95% (Z = 1.645)
- Ordering cost: ₹500/order (assumed, adjustable in `inventory_logic.py`)
- Holding cost: 20% of unit cost per year (standard industry assumption)
- Assumed downtime duration if a stockout occurs: 8 hours (1 shift)
- Criticality multiplier on safety stock ranges from 1.0x (criticality 1) to
  1.8x (criticality 5)
