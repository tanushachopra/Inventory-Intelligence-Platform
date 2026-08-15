import streamlit as st
import pandas as pd
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))
from utils import load_inventory_recommendations
from theme import inject_custom_css, metric_card, section_header, page_header, status_pill

st.set_page_config(page_title="Reorder Recommendations", page_icon="📦", layout="wide")
inject_custom_css()
page_header("📦", "Reorder Recommendations",
            "Criticality- and variability-weighted safety stock, reorder points, EOQ, "
            "and recommended order quantities for every component.")

df = load_inventory_recommendations()

col1, col2, col3 = st.columns(3)
with col1:
    status_filter = st.multiselect("Filter by Status", options=df["reorder_status"].unique(),
                                    default=list(df["reorder_status"].unique()))
with col2:
    machine_filter = st.multiselect("Filter by Machine Type", options=sorted(df["machine_type"].unique()),
                                     default=sorted(df["machine_type"].unique()))
with col3:
    crit_filter = st.slider("Minimum Criticality Score", 1, 5, 1)

filtered = df[
    df["reorder_status"].isin(status_filter)
    & df["machine_type"].isin(machine_filter)
    & (df["criticality_score"] >= crit_filter)
].copy()

st.write("")
col1, col2, col3 = st.columns(3)
with col1:
    metric_card("Items Shown", len(filtered))
with col2:
    metric_card("Urgent Among These", (filtered["reorder_status"] == "URGENT - Order Now").sum(), accent=True)
with col3:
    metric_card("Total Downtime Risk", f"₹{filtered['estimated_downtime_cost'].sum():,.0f}", accent=True)

st.write("")
filtered["Status"] = filtered["reorder_status"].apply(lambda s: status_pill(s))
display_cols = [
    "component_id", "component_name", "machine_type", "criticality_score",
    "current_stock", "reorder_point", "safety_stock", "eoq", "recommended_order_qty",
    "days_to_stockout", "Status", "estimated_downtime_cost",
]

html_table = filtered[display_cols].rename(columns={
    "component_id": "Component", "component_name": "Name", "machine_type": "Machine Type",
    "criticality_score": "Criticality", "current_stock": "Current Stock",
    "reorder_point": "Reorder Point", "safety_stock": "Safety Stock", "eoq": "EOQ",
    "recommended_order_qty": "Recommended Order Qty", "days_to_stockout": "Days to Stockout",
    "estimated_downtime_cost": "Downtime Risk (₹)",
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

section_header("What-If: Adjust Lead Time Assumption",
               "See how a supplier delay (or improvement) would shift reorder points.")

lead_time_adjustment = st.slider("Lead Time Adjustment (days, +/-)", -5, 10, 0)

demo = filtered.copy()
demo["adjusted_reorder_point"] = demo["reorder_point"] * (
    1 + (lead_time_adjustment / demo["days_to_stockout"].clip(lower=1)) * 0.1
)
demo["would_flip_to_reorder"] = (
    (demo["current_stock"] <= demo["adjusted_reorder_point"]) & (demo["reorder_status"] == "Healthy")
)
newly_at_risk = demo["would_flip_to_reorder"].sum()

if lead_time_adjustment > 0:
    st.markdown(f'<div class="alert-card critical">⚠️ If supplier lead times increased by '
                f'{lead_time_adjustment} days, an estimated <b>{newly_at_risk} additional components</b> '
                f'currently marked \'Healthy\' would move into reorder territory.</div>', unsafe_allow_html=True)
elif lead_time_adjustment < 0:
    st.markdown(f'<div class="alert-card ok">✅ If lead times were reduced by '
                f'{abs(lead_time_adjustment)} days, reorder points would tighten, giving more buffer '
                f'before stockout risk across the board.</div>', unsafe_allow_html=True)
else:
    st.caption("Move the slider to simulate a longer or shorter supplier lead time.")
