import streamlit as st
import pandas as pd
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))
from utils import load_inventory_recommendations, load_machine_risk, load_components
from theme import inject_custom_css, metric_card, section_header, page_header, TEXT_MUTED

st.set_page_config(page_title="Alerts", page_icon="🚨", layout="wide")
inject_custom_css()
page_header("🚨", "Alerts", "All urgent stockout and machine-risk warnings in one place, with estimated cost impact.")

inventory = load_inventory_recommendations()
risk = load_machine_risk()
components = load_components()

urgent = inventory[inventory["reorder_status"] == "URGENT - Order Now"].sort_values(
    "estimated_downtime_cost", ascending=False
)
at_risk = risk[risk["maintenance_status"] == "AT RISK - Before Scheduled Maintenance"]

col1, col2, col3 = st.columns(3)
with col1:
    metric_card("Urgent Stockout Alerts", len(urgent), accent=True)
with col2:
    metric_card("Machine Risk Alerts", len(at_risk), accent=True)
with col3:
    metric_card("Total Downtime Exposure", f"₹{urgent['estimated_downtime_cost'].sum():,.0f}", accent=True)

st.write("")
st.markdown("---")
st.write("")

section_header("📦 Stockout Risk Alerts (Demand-Driven)")

if len(urgent) > 0:
    for _, row in urgent.iterrows():
        st.markdown(f"""
        <div class="alert-card critical">
            <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap;">
                <div style="flex:2; min-width:250px;">
                    <b style="font-size:15px;">{row['component_id']} — {row['component_name']}</b><br>
                    <span style="color:{TEXT_MUTED}; font-size:13px;">
                        Machine: {row['machine_type']} ({row['linked_machine_id']}) · Criticality {row['criticality_score']}/5
                    </span><br>
                    <span style="color:{TEXT_MUTED}; font-size:13px;">
                        Recommended: order <b style="color:#F5A623;">{row['recommended_order_qty']:.0f} units</b>
                        (lead time {row['lead_time_days']} days)
                    </span>
                </div>
                <div style="flex:1; text-align:right; min-width:150px;">
                    <div style="font-size:12px; color:{TEXT_MUTED}; text-transform:uppercase;">Days to Stockout</div>
                    <div style="font-size:22px; font-weight:800; color:#F87171; font-family:'JetBrains Mono',monospace;">
                        {int(row['days_to_stockout']) if pd.notna(row['days_to_stockout']) else '—'}
                    </div>
                    <div style="font-size:12px; color:{TEXT_MUTED}; margin-top:6px;">Downtime Risk</div>
                    <div style="font-size:16px; font-weight:700; color:#F5A623;">₹{row['estimated_downtime_cost']:,.0f}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
else:
    st.markdown('<div class="alert-card ok">✅ No urgent stockout risks right now.</div>', unsafe_allow_html=True)

st.write("")
st.markdown("---")
st.write("")

section_header("🛠️ Machine Risk Alerts (Maintenance-Driven)")

if len(at_risk) > 0:
    for _, row in at_risk.iterrows():
        linked_components = components[components["linked_machine_id"] == row["machine_id"]]
        comp_list = ", ".join(linked_components["component_id"].tolist()) if len(linked_components) > 0 else "None linked"
        st.markdown(f"""
        <div class="alert-card critical">
            <b style="font-size:15px;">{row['machine_id']} — {row['machine_type']}</b>
            <span style="color:{TEXT_MUTED};"> (Criticality {row['criticality_score']}/5)</span><br>
            <span style="color:{TEXT_MUTED}; font-size:13px;">
                Health score {row['current_health_score']} · Predicted critical risk in
                <b style="color:#F87171;">{int(row['days_to_critical_risk'])} days</b> — before scheduled maintenance
            </span><br>
            <span style="color:{TEXT_MUTED}; font-size:13px;">Linked components: {comp_list}</span>
        </div>
        """, unsafe_allow_html=True)
else:
    st.markdown('<div class="alert-card ok">✅ No machines currently at risk ahead of their scheduled maintenance.</div>',
                unsafe_allow_html=True)

st.write("")
st.caption("Demand-driven alerts come from the XGBoost consumption forecast + inventory formulas. "
           "Maintenance-driven alerts come from the machine health ML model, independent of demand patterns.")
