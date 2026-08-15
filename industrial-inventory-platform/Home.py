import streamlit as st
import pandas as pd
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "src"))
from utils import (
    load_machines, load_components, load_inventory_recommendations,
    load_machine_risk
)
from theme import inject_custom_css, metric_card, status_pill, section_header, page_header, TEXT_MUTED

st.set_page_config(
    page_title="Industrial Inventory Intelligence Platform",
    page_icon="🏭",
    layout="wide",
)
inject_custom_css()

page_header(
    "🏭", "Industrial Inventory Intelligence Platform",
    "Forecasts component demand, prioritizes reorders by machine criticality, "
    "and links inventory decisions to predicted machine health."
)

machines = load_machines()
components = load_components()
inventory = load_inventory_recommendations()
risk = load_machine_risk()

# --- Top-level KPI cards ---
col1, col2, col3, col4 = st.columns(4)

with col1:
    metric_card("Machines Monitored", len(machines), "Across the plant floor")

with col2:
    metric_card("Components Tracked", len(components), "Materials, parts & consumables")

with col3:
    urgent_count = (inventory["reorder_status"] == "URGENT - Order Now").sum()
    metric_card("Urgent Reorders", urgent_count, "Needs action now", accent=True)

with col4:
    total_downtime_risk = inventory["estimated_downtime_cost"].sum()
    metric_card("Downtime Risk Exposure", f"₹{total_downtime_risk:,.0f}", "If urgent items stock out", accent=True)

st.write("")
st.write("")

col_left, col_right = st.columns(2)

with col_left:
    section_header("Reorder Status Breakdown")
    status_counts = inventory["reorder_status"].value_counts().reset_index()
    status_counts.columns = ["Status", "Count"]
    st.bar_chart(status_counts.set_index("Status"), color=["#F5A623"])

with col_right:
    section_header("Machine Health Status")
    maint_counts = risk["maintenance_status"].value_counts().reset_index()
    maint_counts.columns = ["Status", "Count"]
    st.bar_chart(maint_counts.set_index("Status"), color=["#2DD4BF"])

st.write("")
st.markdown("---")
st.write("")

section_header("⚠️ Machines Needing Attention", "Predicted to hit critical failure risk before scheduled maintenance")
at_risk = risk[risk["maintenance_status"] == "AT RISK - Before Scheduled Maintenance"]

if len(at_risk) > 0:
    for _, row in at_risk.iterrows():
        st.markdown(f"""
        <div class="alert-card critical">
            <b>{row['machine_id']} — {row['machine_type']}</b><br>
            <span style="color:{TEXT_MUTED}; font-size:13px;">
            Health score {row['current_health_score']} · Predicted critical risk in
            <b style="color:#F87171;">{int(row['days_to_critical_risk'])} days</b> ·
            Scheduled maintenance in {int(row['days_to_scheduled_maintenance'])} days
            </span>
        </div>
        """, unsafe_allow_html=True)
else:
    st.markdown('<div class="alert-card ok">✅ All machines are on track with scheduled maintenance.</div>',
                unsafe_allow_html=True)

st.write("")
st.caption("Use the sidebar to navigate: Demand Forecasts, Reorder Recommendations, "
           "Maintenance & Machine Health, Maintenance Calendar, and Alerts.")
