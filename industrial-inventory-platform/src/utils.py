"""Shared data-loading utilities for all Streamlit pages."""

import os
import pandas as pd
import streamlit as st

# Resolve DATA_DIR relative to THIS file's location (src/utils.py), not the
# current working directory. This makes data loading work correctly no
# matter where the app is launched from -- local VS Code, a nested GitHub
# repo folder, or Streamlit Cloud's /mount/src/... path.
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "processed")


@st.cache_data
def load_machines():
    return pd.read_csv(f"{DATA_DIR}/machines.csv")


@st.cache_data
def load_components():
    return pd.read_csv(f"{DATA_DIR}/components.csv")


@st.cache_data
def load_consumption():
    return pd.read_csv(f"{DATA_DIR}/consumption.csv", parse_dates=["date"])


@st.cache_data
def load_forecast():
    return pd.read_csv(f"{DATA_DIR}/forecast_next_30_days.csv", parse_dates=["date"])


@st.cache_data
def load_inventory_recommendations():
    return pd.read_csv(f"{DATA_DIR}/inventory_recommendations.csv")


@st.cache_data
def load_machine_risk():
    return pd.read_csv(f"{DATA_DIR}/machine_risk_projection.csv")


@st.cache_data
def load_machine_health():
    return pd.read_csv(f"{DATA_DIR}/machine_health.csv", parse_dates=["date"])


@st.cache_data
def load_maintenance_calendar():
    return pd.read_csv(f"{DATA_DIR}/maintenance_calendar.csv", parse_dates=["scheduled_date"])


def status_color(status):
    """Return a color for reorder/maintenance status badges."""
    mapping = {
        "URGENT - Order Now": "🔴",
        "AT RISK - Before Scheduled Maintenance": "🔴",
        "Reorder Soon": "🟠",
        "Monitor - Maintenance Scheduled In Time": "🟡",
        "Healthy": "🟢",
        "Stable": "🟢",
    }
    return mapping.get(status, "⚪")