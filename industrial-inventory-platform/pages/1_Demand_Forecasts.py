import streamlit as st
import pandas as pd
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))
from utils import load_machines, load_components, load_consumption, load_forecast
from theme import inject_custom_css, metric_card, section_header, page_header

st.set_page_config(page_title="Demand Forecasts", page_icon="📈", layout="wide")
inject_custom_css()
page_header("📈", "Demand Forecasts", "Historical consumption vs. the next 30-day forecast for any machine-component pair.")

machines = load_machines()
components = load_components()
consumption = load_consumption()
forecast = load_forecast()

col1, col2 = st.columns(2)
with col1:
    machine_choice = st.selectbox(
        "Select Machine",
        options=machines["machine_id"] + " — " + machines["machine_type"],
    )
    machine_id = machine_choice.split(" — ")[0]

with col2:
    machine_components = components[components["linked_machine_id"] == machine_id]
    if len(machine_components) == 0:
        st.warning("No components linked to this machine.")
        st.stop()
    component_choice = st.selectbox(
        "Select Component",
        options=machine_components["component_id"] + " — " + machine_components["component_name"],
    )
    component_id = component_choice.split(" — ")[0]

hist = consumption[
    (consumption["machine_id"] == machine_id) & (consumption["component_id"] == component_id)
].groupby("date", as_index=False)["qty_consumed"].sum()

fut = forecast[
    (forecast["machine_id"] == machine_id) & (forecast["component_id"] == component_id)
][["date", "forecast_qty"]].rename(columns={"forecast_qty": "qty_consumed"})

hist_recent = hist.tail(90).copy()
hist_recent["type"] = "Historical"
fut_c = fut.copy()
fut_c["type"] = "Forecast"

combined = pd.concat([hist_recent, fut_c])
chart_data = combined.pivot(index="date", columns="type", values="qty_consumed")

st.write("")
section_header(f"{component_id} consumption on {machine_id}")
st.line_chart(chart_data, color=["#2DD4BF", "#F5A623"])

st.write("")
col1, col2, col3 = st.columns(3)
with col1:
    metric_card("Avg Daily (last 90d)", f"{hist_recent['qty_consumed'].mean():.1f}")
with col2:
    metric_card("Forecasted Avg (next 30d)", f"{fut['qty_consumed'].mean():.1f}", accent=True)
with col3:
    change = fut['qty_consumed'].mean() - hist_recent['qty_consumed'].mean()
    metric_card("Expected Change", f"{change:+.1f}", accent=(change != 0))

st.write("")
with st.expander("View raw forecast data"):
    st.dataframe(fut[["date", "qty_consumed"]].rename(columns={"qty_consumed": "forecast_qty"}),
                 use_container_width=True)
