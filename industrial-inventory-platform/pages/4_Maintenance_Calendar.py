import streamlit as st
import pandas as pd
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))
from utils import load_maintenance_calendar, load_machines, load_machine_risk
from theme import inject_custom_css, metric_card, section_header, page_header

st.set_page_config(page_title="Maintenance Calendar", page_icon="🗓️", layout="wide")
inject_custom_css()
page_header("🗓️", "Maintenance Calendar",
            "Upcoming scheduled maintenance across all machines, cross-referenced with "
            "predicted risk so you can see if any maintenance is happening too late.")

calendar = load_maintenance_calendar()
machines = load_machines()
risk = load_machine_risk()

TODAY_REF = pd.Timestamp("2025-12-31")

calendar = calendar.merge(machines[["machine_id", "machine_type", "criticality_score"]], on="machine_id")
calendar = calendar.merge(
    risk[["machine_id", "days_to_critical_risk", "maintenance_status"]], on="machine_id", how="left"
)

upcoming = calendar[calendar["scheduled_date"] >= TODAY_REF].sort_values("scheduled_date").copy()
upcoming["days_from_today"] = (upcoming["scheduled_date"] - TODAY_REF).dt.days

col1, col2 = st.columns(2)
with col1:
    machine_filter = st.multiselect("Filter by Machine", options=sorted(upcoming["machine_id"].unique()),
                                     default=sorted(upcoming["machine_id"].unique()))
with col2:
    horizon = st.slider("Show maintenance within next N days", 30, 365, 180)

filtered = upcoming[
    upcoming["machine_id"].isin(machine_filter) & (upcoming["days_from_today"] <= horizon)
].copy()


def risk_note(row):
    if pd.notna(row["days_to_critical_risk"]) and row["days_to_critical_risk"] < row["days_from_today"]:
        return f"⚠️ At-risk {int(row['days_from_today'] - row['days_to_critical_risk'])}d before this maintenance"
    return "✅ On track"


filtered["risk_note"] = filtered.apply(risk_note, axis=1)

st.write("")
col1, col2, col3 = st.columns(3)
with col1:
    metric_card("Events in Window", len(filtered))
with col2:
    metric_card("Machines Covered", filtered["machine_id"].nunique())
with col3:
    flagged_count = (filtered["risk_note"] != "✅ On track").sum()
    metric_card("Flagged as Late", flagged_count, accent=True)

st.write("")
section_header(f"Upcoming Maintenance (next {horizon} days)")

html_table = filtered[[
    "scheduled_date", "machine_id", "machine_type", "maintenance_type",
    "criticality_score", "days_from_today", "risk_note"
]].rename(columns={
    "scheduled_date": "Scheduled Date", "machine_id": "Machine", "machine_type": "Type",
    "maintenance_type": "Maintenance Type", "criticality_score": "Criticality",
    "days_from_today": "Days From Today", "risk_note": "Risk Note",
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

section_header("Timeline View")
timeline_data = filtered.copy()
timeline_data["machine_label"] = timeline_data["machine_id"] + " (" + timeline_data["machine_type"] + ")"

if len(timeline_data) > 0:
    chart = timeline_data.pivot_table(
        index="scheduled_date", columns="machine_label", values="days_from_today", aggfunc="first"
    ).notna().astype(int)
    st.bar_chart(chart)
else:
    st.info("No maintenance events in the selected window.")

st.write("")
flagged = filtered[filtered["risk_note"] != "✅ On track"]
if len(flagged) > 0:
    st.markdown(f'<div class="alert-card critical">⚠️ <b>{len(flagged)} scheduled maintenance event(s)</b> '
                f'are predicted to happen after the machine is already expected to hit critical failure risk. '
                f'Consider moving these up.</div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="alert-card ok">✅ All upcoming maintenance is scheduled ahead of predicted critical risk.</div>',
                unsafe_allow_html=True)
