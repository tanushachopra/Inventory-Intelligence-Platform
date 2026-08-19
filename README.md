# Industrial Inventory Intelligence Platform

An ML-driven platform that forecasts component/material consumption for a
manufacturing plant, computes criticality- and variability-weighted reorder
points and EOQ, and cross-references machine health predictions to flag
maintenance-linked reorders before a stockout causes downtime.

## Live Demo : https://stocksensemarket.streamlit.app

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

## How to run it locally

pip install -r requirements.txt --break-system-packages
streamlit run Home.py

## Model performance

- Demand forecasting (XGBoost): MAE ≈ 2.6% of average daily consumption
  (tested on the most recent 90 days, unseen during training)
- Failure risk model (XGBoost): R² ≈ 0.95

## Assumptions used

- Service level for safety stock: 95% (Z = 1.645)
- Ordering cost: ₹500/order (assumed, adjustable in inventory_logic.py)
- Holding cost: 20% of unit cost per year
- Assumed downtime duration if a stockout occurs: 8 hours (1 shift)
- Criticality multiplier on safety stock ranges from 1.0x to 1.8x
