import streamlit as st
import pandas as pd
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))
from utils import load_machine_risk, load_machine_health, load_components
from theme import inject_custom_css, metric_card, section_header, page_header, status_pill

st.set_page_config(page_title="Maintenance & Machine Health", page_icon="🛠️", layout="wide")
inject_custom_css()
page_header("🛠️", "Maintenance & Machine Health",
            "ML-predicted failure risk per machine, projected days until critical risk, "
            "and which components get flagged for reorder as a result.")

risk = load_machine_risk()
health = load_machine_health()
components = load_components()

section_header("Machine Risk Projection")
risk_display = risk.copy()
risk_display["Status"] = risk_display["maintenance_status"].apply(status_pill)

html_table = risk_display[[
    "machine_id", "machine_type", "criticality_score", "current_health_score",
    "current_failure_risk", "days_to_critical_risk", "days_to_scheduled_maintenance", "Status"
]].rename(columns={
    "machine_id": "Machine", "machine_type": "Type", "criticality_score": "Criticality",
    "current_health_score": "Health Score", "current_failure_risk": "Failure Risk",
    "days_to_critical_risk": "Days to Critical Risk",
    "days_to_scheduled_maintenance": "Days to Scheduled Maintenance",
}).to_html(escape=False, index=False)

st.markdown(f"""
<div style="overflow-x:auto; border:1px solid #2A313C; border-radius:10px;">
<style>
    table {{ width:100%; border-collapse: collapse; font-size: 13px; }}
    th {{ background-color: #161B22; color: #9AA4B2; text-transform:uppercase; font-size:11px;
          letter-spacing:0.05em; padding:12px 10px; text-align:left; border-bottom:1px solid #2A313C; }}
    td {{ padding:10px; border-bottom:1px solid #1E242C; color:#E6E6E6; }}
    tr:hover {{ background-color: #161B22; }}
</style>
{html_table}
</div>
""", unsafe_allow_html=True)

st.write("")
st.markdown("---")
st.write("")

section_header("Sensor Trend for a Machine")
machine_choice = st.selectbox("Select Machine", options=risk["machine_id"])
machine_health = health[health["machine_id"] == machine_choice].sort_values("date").tail(120)

col1, col2 = st.columns(2)
with col1:
    st.caption("Health Score (100 = perfect, trending down = wear increasing)")
    st.line_chart(machine_health.set_index("date")[["health_score"]], color=["#2DD4BF"])
with col2:
    st.caption("Failure Risk (model-predicted, accelerates near end of cycle)")
    st.line_chart(machine_health.set_index("date")[["failure_risk"]], color=["#F87171"])

col3, col4 = st.columns(2)
with col3:
    st.caption("Tool Wear (minutes)")
    st.line_chart(machine_health.set_index("date")[["tool_wear_min"]], color=["#F5A623"])
with col4:
    st.caption("Torque & Rotational Speed")
    st.line_chart(machine_health.set_index("date")[["torque_Nm", "rotational_speed_rpm"]])

st.write("")
st.markdown("---")
st.write("")

section_header("Components Flagged for Maintenance-Linked Reorder")
flagged = components[components["maintenance_triggered_reorder"] == True]

if len(flagged) > 0:
    html_table2 = flagged[["component_id", "component_name", "category", "linked_machine_id", "lead_time_days"]].rename(
        columns={"component_id": "Component", "component_name": "Name", "category": "Category",
                 "linked_machine_id": "Machine", "lead_time_days": "Lead Time (days)"}
    ).to_html(escape=False, index=False)
    st.markdown(f"""
    <div style="overflow-x:auto; border:1px solid #2A313C; border-radius:10px;">
    <style>
        table {{ width:100%; border-collapse: collapse; font-size: 13px; }}
        th {{ background-color: #161B22; color: #9AA4B2; text-transform:uppercase; font-size:11px;
              letter-spacing:0.05em; padding:12px 10px; text-align:left; border-bottom:1px solid #2A313C; }}
        td {{ padding:10px; border-bottom:1px solid #1E242C; color:#E6E6E6; }}
    </style>
    {html_table2}
    </div>
    """, unsafe_allow_html=True)
    st.write("")
    st.markdown(f'<div class="alert-card critical">⚠️ These {len(flagged)} components are linked to '
                f'machines predicted to hit critical failure risk before their next scheduled maintenance — '
                f'flagged independent of demand forecasting.</div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="alert-card ok">✅ No components currently flagged by maintenance risk.</div>',
                unsafe_allow_html=True)
