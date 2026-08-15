"""Shared data-loading utilities for all Streamlit pages."""

import pandas as pd
import streamlit as st

DATA_DIR = "data/processed"


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
