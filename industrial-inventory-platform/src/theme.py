"""
Custom theming for the Industrial Inventory Intelligence Platform.
Injects Google Fonts + custom CSS for a premium dark-industrial look,
and provides reusable HTML component builders (metric cards, status pills,
section headers) used across all pages.
"""

import streamlit as st

ACCENT = "#F5A623"       # industrial amber
ACCENT_TEAL = "#2DD4BF"  # secondary accent
BG_CARD = "#161B22"
BG_CARD_HOVER = "#1C232D"
BORDER = "#2A313C"
TEXT_MUTED = "#9AA4B2"

STATUS_COLORS = {
    "URGENT - Order Now": ("#F87171", "#3A1E1E"),
    "AT RISK - Before Scheduled Maintenance": ("#F87171", "#3A1E1E"),
    "Reorder Soon": ("#FBBF24", "#3A2E12"),
    "Monitor - Maintenance Scheduled In Time": ("#FBBF24", "#3A2E12"),
    "Healthy": ("#4ADE80", "#123A22"),
    "Stable": ("#4ADE80", "#123A22"),
}


def inject_custom_css():
    st.markdown(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

        html, body, [class*="css"] {{
            font-family: 'Inter', sans-serif;
        }}

        /* Hide default streamlit chrome */
        #MainMenu {{visibility: hidden;}}
        footer {{visibility: hidden;}}
        header {{visibility: hidden;}}

        /* Main background with subtle gradient */
        .stApp {{
            background: radial-gradient(circle at 20% 0%, #161C26 0%, #0E1117 45%);
        }}

        /* Sidebar styling */
        section[data-testid="stSidebar"] {{
            background-color: #10141A;
            border-right: 1px solid {BORDER};
        }}
        section[data-testid="stSidebar"] * {{
            font-family: 'Inter', sans-serif;
        }}

        /* Page title styling */
        h1 {{
            font-weight: 800 !important;
            letter-spacing: -0.02em;
            background: linear-gradient(90deg, #FFFFFF 0%, #C9CED6 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            padding-bottom: 4px;
        }}
        h2, h3 {{
            font-weight: 700 !important;
            color: #F0F2F5 !important;
            letter-spacing: -0.01em;
        }}

        /* Custom metric cards */
        .metric-card {{
            background: linear-gradient(145deg, {BG_CARD} 0%, #12161D 100%);
            border: 1px solid {BORDER};
            border-radius: 14px;
            padding: 20px 22px;
            box-shadow: 0 4px 24px rgba(0,0,0,0.25);
            transition: all 0.2s ease;
            height: 100%;
        }}
        .metric-card:hover {{
            border-color: {ACCENT};
            transform: translateY(-2px);
        }}
        .metric-label {{
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: {TEXT_MUTED};
            margin-bottom: 8px;
        }}
        .metric-value {{
            font-size: 30px;
            font-weight: 800;
            color: #F5F7FA;
            font-family: 'JetBrains Mono', monospace;
        }}
        .metric-accent {{
            color: {ACCENT};
        }}
        .metric-sub {{
            font-size: 12px;
            color: {TEXT_MUTED};
            margin-top: 4px;
        }}

        /* Status pills */
        .status-pill {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 100px;
            font-size: 12px;
            font-weight: 600;
            letter-spacing: 0.02em;
        }}

        /* Alert cards */
        .alert-card {{
            background: {BG_CARD};
            border: 1px solid {BORDER};
            border-left: 4px solid {ACCENT};
            border-radius: 10px;
            padding: 16px 20px;
            margin-bottom: 12px;
        }}
        .alert-card.critical {{ border-left-color: #F87171; }}
        .alert-card.ok {{ border-left-color: #4ADE80; }}

        /* Dataframe styling */
        [data-testid="stDataFrame"] {{
            border: 1px solid {BORDER};
            border-radius: 10px;
            overflow: hidden;
        }}

        /* Sidebar nav link spacing */
        section[data-testid="stSidebar"] .css-1544g2n {{
            padding-top: 1rem;
        }}

        /* Divider styling */
        hr {{
            border-color: {BORDER} !important;
        }}

        /* Buttons */
        .stButton>button {{
            background-color: {ACCENT};
            color: #14171C;
            font-weight: 700;
            border: none;
            border-radius: 8px;
        }}
        .stButton>button:hover {{
            background-color: #FFC24D;
            color: #14171C;
        }}
    </style>
    """, unsafe_allow_html=True)


def metric_card(label, value, sub=None, accent=False):
    """Render one custom premium metric card."""
    value_class = "metric-value metric-accent" if accent else "metric-value"
    sub_html = f'<div class="metric-sub">{sub}</div>' if sub else ""
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="{value_class}">{value}</div>
        {sub_html}
    </div>
    """, unsafe_allow_html=True)


def status_pill(status):
    """Return an HTML span for a colored status pill."""
    color, bg = STATUS_COLORS.get(status, ("#9AA4B2", "#2A313C"))
    return f'<span class="status-pill" style="color:{color}; background-color:{bg};">{status}</span>'


def section_header(title, subtitle=None):
    sub_html = f'<p style="color:{TEXT_MUTED}; font-size:14px; margin-top:-8px;">{subtitle}</p>' if subtitle else ""
    st.markdown(f"""
    <h3 style="margin-bottom:2px;">{title}</h3>
    {sub_html}
    """, unsafe_allow_html=True)


def page_header(icon, title, caption):
    st.markdown(f"""
    <div style="margin-bottom: 24px;">
        <h1 style="margin-bottom:4px;">{icon} {title}</h1>
        <p style="color:{TEXT_MUTED}; font-size:15px; margin-top:0;">{caption}</p>
    </div>
    """, unsafe_allow_html=True)
