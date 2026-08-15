import streamlit as st
import pandas as pd
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))
from theme import inject_custom_css, metric_card, section_header, page_header, TEXT_MUTED

st.set_page_config(page_title="ABC-VED Analysis", page_icon="🎯", layout="wide")
inject_custom_css()
page_header("🎯", "ABC-VED Analysis",
            "Classic operations-management prioritization: ABC ranks components by "
            "annual consumption value, VED ranks by operational criticality. Combined, "
            "they tell you exactly where to focus inventory control effort.")

DATA_DIR = "data/processed"


@st.cache_data
def load_abc_ved():
    return pd.read_csv(f"{DATA_DIR}/abc_ved_classification.csv")


df = load_abc_ved()

col1, col2, col3, col4 = st.columns(4)
with col1:
    metric_card("Class A Items", (df["abc_class"] == "A").sum(), "~70% of total value")
with col2:
    metric_card("Class B Items", (df["abc_class"] == "B").sum(), "~20% of total value")
with col3:
    metric_card("Class C Items", (df["abc_class"] == "C").sum(), "~10% of total value")
with col4:
    metric_card("Vital Items", (df["ved_class"] == "V").sum(), "Stockout stops production", accent=True)

st.write("")
st.markdown("---")
st.write("")

section_header("ABC x VED Matrix", "Count of components in each combined category")

matrix = pd.crosstab(df["abc_class"], df["ved_class"]).reindex(
    index=["A", "B", "C"], columns=["V", "E", "D"], fill_value=0
)

cell_colors = {
    "AV": "#F87171", "AE": "#FB923C", "AD": "#FBBF24",
    "BV": "#FB923C", "BE": "#FBBF24", "BD": "#A3E635",
    "CV": "#FBBF24", "CE": "#A3E635", "CD": "#4ADE80",
}

cols = st.columns(3)
for i, ved in enumerate(["V", "E", "D"]):
    with cols[i]:
        st.markdown(f"<div style='text-align:center; color:{TEXT_MUTED}; font-weight:600; "
                    f"text-transform:uppercase; font-size:12px; margin-bottom:8px;'>{ved} "
                    f"({'Vital' if ved=='V' else 'Essential' if ved=='E' else 'Desirable'})</div>",
                    unsafe_allow_html=True)
        for abc in ["A", "B", "C"]:
            key = abc + ved
            count = matrix.loc[abc, ved]
            color = cell_colors.get(key, "#4ADE80")
            st.markdown(f"""
            <div style="background:{color}22; border:1px solid {color}; border-radius:10px;
                        padding:16px; text-align:center; margin-bottom:10px;">
                <div style="font-size:11px; color:{TEXT_MUTED}; text-transform:uppercase; letter-spacing:0.05em;">{key}</div>
                <div style="font-size:26px; font-weight:800; color:{color}; font-family:'JetBrains Mono',monospace;">{count}</div>
            </div>
            """, unsafe_allow_html=True)

st.write("")
st.markdown("---")
st.write("")

section_header("🔺 Highest Priority: Vital Items", "Regardless of value class, these need guaranteed availability")
vital = df[df["ved_class"] == "V"].sort_values("annual_value", ascending=False)

for _, row in vital.iterrows():
    st.markdown(f"""
    <div class="alert-card critical">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap;">
            <div>
                <b>{row['component_id']} — {row['component_name']}</b>
                <span style="background:#F5A62322; color:#F5A623; padding:2px 8px; border-radius:6px;
                             font-size:11px; font-weight:700; margin-left:8px;">{row['abc_ved']}</span><br>
                <span style="color:{TEXT_MUTED}; font-size:13px;">{row['machine_type']} · Annual value ₹{row['annual_value']:,.0f}</span>
            </div>
        </div>
        <div style="color:{TEXT_MUTED}; font-size:12px; margin-top:8px;">{row['control_policy']}</div>
    </div>
    """, unsafe_allow_html=True)

st.write("")
st.markdown("---")
st.write("")

section_header("Full Classification Table")

col1, col2 = st.columns(2)
with col1:
    abc_filter = st.multiselect("Filter ABC Class", options=["A", "B", "C"], default=["A", "B", "C"])
with col2:
    ved_filter = st.multiselect("Filter VED Class", options=["V", "E", "D"], default=["V", "E", "D"])

filtered = df[df["abc_class"].isin(abc_filter) & df["ved_class"].isin(ved_filter)]

html_table = filtered[[
    "component_id", "component_name", "machine_type", "annual_value",
    "abc_ved", "control_policy"
]].rename(columns={
    "component_id": "Component", "component_name": "Name", "machine_type": "Machine",
    "annual_value": "Annual Value (₹)", "abc_ved": "Class", "control_policy": "Recommended Control Policy",
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
st.caption("ABC classification: Pareto-based on annual consumption value (top ~70% cumulative = A, "
           "next ~20% = B, remaining ~10% = C). VED classification: based on machine criticality score "
           "(4-5 = Vital, 3 = Essential, 1-2 = Desirable).")