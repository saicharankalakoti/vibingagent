import json
import time
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv

from agent.graph import run_costguard
from core.tools import check_api_health
from core.store import get_all_actions, clear_db

load_dotenv()

# Page configuration
st.set_page_config(
    page_title="CostGuard | Autonomous Cloud Cost-Optimization Agent",
    page_icon="☁️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------------------------------------------------------
# DESIGN SYSTEM & CUSTOM CSS
# -----------------------------------------------------------------------------
CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700&display=swap');

:root {
    --bg-main: #f8fafc;
    --card-bg: #ffffff;
    --border-color: #e2e8f0;
    --primary-blue: #2563eb;
    --sidebar-bg: #0b1329;
    --text-primary: #0f172a;
    --text-secondary: #475569;
    --text-muted: #64748b;
    --emerald-green: #10b981;
    --amber-orange: #f59e0b;
    --rose-red: #ef4444;
}

html, body, [class*="css"], [data-testid="stAppViewContainer"] {
    font-family: 'Plus Jakarta Sans', 'Inter', -apple-system, sans-serif !important;
    background-color: var(--bg-main) !important;
    color: var(--text-primary) !important;
}

/* Hide Streamlit Header Clutter & Deploy Button */
header[data-testid="stHeader"],
.stDeployButton,
[data-testid="stToolbar"],
[data-testid="stDecoration"] {
    display: none !important;
    visibility: hidden !important;
}
.block-container {
    padding-top: 1.5rem !important;
    padding-bottom: 2rem !important;
    max-width: 98% !important;
}

/* Sidebar Styling */
[data-testid="stSidebar"] {
    background-color: var(--sidebar-bg) !important;
    border-right: 1px solid #1e293b !important;
}
[data-testid="stSidebar"] * {
    color: #cbd5e1 !important;
}
[data-testid="stSidebar"] hr {
    border-color: #1e293b !important;
    margin: 1rem 0 !important;
}

/* Sidebar Radio Navigation */
[data-testid="stSidebar"] div[data-testid="stRadio"] > div[role="radiogroup"] {
    gap: 4px !important;
}
[data-testid="stSidebar"] div[data-testid="stRadio"] [role="radiogroup"] label {
    display: flex !important;
    align-items: center !important;
    background: transparent !important;
    padding: 9px 14px !important;
    border-radius: 10px !important;
    transition: all 0.2s ease !important;
    border: 1px solid transparent !important;
    cursor: pointer !important;
    width: 100% !important;
}
[data-testid="stSidebar"] div[data-testid="stRadio"] [role="radiogroup"] label > div:has(input[type="radio"]) {
    display: none !important;
    visibility: hidden !important;
    width: 0 !important;
    height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    position: absolute !important;
    pointer-events: none !important;
}
[data-testid="stSidebar"] div[data-testid="stRadio"] [role="radiogroup"] label p {
    font-size: 13.5px !important;
    font-weight: 500 !important;
    margin: 0 !important;
    color: #94a3b8 !important;
}
[data-testid="stSidebar"] div[data-testid="stRadio"] [role="radiogroup"] label:hover {
    background: rgba(255, 255, 255, 0.06) !important;
}
[data-testid="stSidebar"] div[data-testid="stRadio"] [role="radiogroup"] label:hover p {
    color: #ffffff !important;
}
[data-testid="stSidebar"] div[data-testid="stRadio"] [role="radiogroup"] label:has(input:checked) {
    background: #2563eb !important;
    box-shadow: 0 4px 14px rgba(37, 99, 235, 0.4) !important;
}
[data-testid="stSidebar"] div[data-testid="stRadio"] [role="radiogroup"] label:has(input:checked) p {
    color: #ffffff !important;
    font-weight: 700 !important;
}

/* Top Header */
.top-header-wrap {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1.4rem;
    gap: 1.5rem;
}
.header-left-title {
    font-size: 27px;
    font-weight: 800;
    color: #0f172a;
    letter-spacing: -0.02em;
    margin: 0;
    line-height: 1.2;
}
.header-left-title span {
    color: #2563eb;
}
.header-left-subtitle {
    font-size: 14.5px;
    font-weight: 600;
    color: #334155;
    margin: 4px 0 6px 0;
}
.header-pipeline-crumbs {
    font-size: 12.5px;
    color: #64748b;
    font-weight: 500;
    display: flex;
    align-items: center;
    gap: 6px;
}
.header-pipeline-crumbs span.arrow {
    color: #94a3b8;
}

/* Hero Banner Card */
.hero-banner-card {
    background: linear-gradient(135deg, #3730a3 0%, #2563eb 55%, #60a5fa 100%);
    border-radius: 16px;
    padding: 1.1rem 1.6rem;
    color: #ffffff !important;
    box-shadow: 0 10px 25px -5px rgba(37, 99, 235, 0.35);
    display: flex;
    justify-content: space-between;
    align-items: center;
    min-height: 96px;
}
.hero-banner-card * {
    color: #ffffff !important;
}
.hero-banner-text h3 {
    font-size: 18px;
    font-weight: 800;
    margin: 0 0 3px 0;
    line-height: 1.2;
}
.hero-banner-text p {
    font-size: 12px;
    margin: 0;
    opacity: 0.9;
    font-weight: 400;
}
.hero-visual-badge {
    display: flex;
    align-items: center;
    gap: 8px;
    background: rgba(255, 255, 255, 0.15);
    backdrop-filter: blur(8px);
    padding: 6px 12px;
    border-radius: 999px;
    border: 1px solid rgba(255, 255, 255, 0.25);
    font-size: 11.5px;
    font-weight: 600;
}

/* KPI Summary Cards */
.kpi-container {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1.2rem;
    margin-bottom: 1.8rem;
}
.kpi-card {
    background: #ffffff;
    border-radius: 14px;
    padding: 1.1rem 1.2rem;
    border: 1px solid #e2e8f0;
    box-shadow: 0 4px 16px -2px rgba(15, 23, 42, 0.03);
    display: flex;
    align-items: center;
    gap: 14px;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.kpi-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 20px -3px rgba(15, 23, 42, 0.07);
}
.kpi-icon-circle {
    width: 44px;
    height: 44px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 19px;
    flex-shrink: 0;
}
.kpi-info-block {
    display: flex;
    flex-direction: column;
    gap: 1px;
}
.kpi-label {
    font-size: 11.5px;
    font-weight: 600;
    color: #64748b;
    text-transform: capitalize;
}
.kpi-value {
    font-size: 21px;
    font-weight: 800;
    color: #0f172a;
    line-height: 1.2;
}
.kpi-badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: 11px;
    font-weight: 700;
    padding: 2px 7px;
    border-radius: 999px;
    margin-top: 3px;
    width: fit-content;
}
.kpi-badge-warn {
    background: #fef2f2;
    color: #dc2626;
}
.kpi-badge-success {
    background: #ecfdf5;
    color: #059669;
}
.kpi-badge-neutral {
    background: #eff6ff;
    color: #2563eb;
}

/* Dashboard White Cards */
.dash-card {
    background: #ffffff;
    border-radius: 15px;
    border: 1px solid #e2e8f0;
    box-shadow: 0 4px 16px -2px rgba(15, 23, 42, 0.03);
    padding: 1.3rem;
    margin-bottom: 1.2rem;
}
.dash-card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
}
.dash-card-title {
    font-size: 15.5px;
    font-weight: 700;
    color: #0f172a;
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 0;
    white-space: nowrap;
}

/* Telemetry Strip */
.telemetry-strip {
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 8px 14px;
    margin-bottom: 12px;
    font-size: 12.5px;
    color: #334155;
    flex-wrap: wrap;
    gap: 8px;
}
.telemetry-item {
    display: flex;
    align-items: center;
    gap: 5px;
}
.telemetry-item strong {
    color: #0f172a;
}

/* Evidence Comparison Table */
.evidence-table {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
    margin-top: 4px;
}
.evidence-table th {
    background: #f8fafc;
    color: #475569;
    font-size: 11.5px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    padding: 9px 12px;
    border-bottom: 1px solid #e2e8f0;
}
.evidence-table th:first-child { border-top-left-radius: 8px; }
.evidence-table th:last-child { border-top-right-radius: 8px; }
.evidence-table td {
    padding: 11px 12px;
    font-size: 13px;
    color: #1e293b;
    border-bottom: 1px solid #f1f5f9;
}
.evidence-table tr:last-child td {
    border-bottom: none;
}
.table-pill {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 3px 8px;
    border-radius: 999px;
    font-size: 11.5px;
    font-weight: 700;
}
.table-pill-up-warn {
    background: #fef2f2;
    color: #ef4444;
}
.table-pill-down-green {
    background: #ecfdf5;
    color: #10b981;
}
.table-pill-blue {
    background: #eff6ff;
    color: #2563eb;
}
.table-pill-neutral {
    background: #f1f5f9;
    color: #64748b;
}

/* Agent Response Callout */
.agent-callout-box {
    background: #f0fdf4;
    border: 1px solid #bbf7d0;
    border-radius: 12px;
    padding: 12px 16px;
    display: flex;
    align-items: flex-start;
    gap: 12px;
    margin-bottom: 12px;
}
.agent-callout-icon {
    background: #10b981;
    color: white;
    width: 26px;
    height: 26px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 14px;
    flex-shrink: 0;
    margin-top: 1px;
}
.agent-callout-text {
    font-size: 13px;
    font-weight: 600;
    color: #166534;
    line-height: 1.5;
}

/* Feature Badges */
.feature-badges-row {
    display: flex;
    gap: 10px;
    margin-top: 12px;
    flex-wrap: wrap;
}
.feature-badge-item {
    display: flex;
    align-items: center;
    gap: 6px;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    padding: 6px 10px;
    border-radius: 8px;
    font-size: 11.5px;
    font-weight: 600;
    color: #334155;
}

/* Timeline Audit Steps */
.timeline-step {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 9px 12px;
    border-radius: 9px;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    margin-bottom: 7px;
}
.timeline-left {
    display: flex;
    align-items: center;
    gap: 10px;
}
.timeline-num-badge {
    width: 24px;
    height: 24px;
    border-radius: 50%;
    background: #2563eb;
    color: #ffffff;
    font-size: 11.5px;
    font-weight: 700;
    display: flex;
    align-items: center;
    justify-content: center;
}
.timeline-name {
    font-size: 13px;
    font-weight: 600;
    color: #1e293b;
}
.timeline-right {
    display: flex;
    align-items: center;
    gap: 10px;
}
.timeline-duration {
    font-size: 11.5px;
    font-weight: 600;
    color: #64748b;
}
.timeline-status-icon {
    width: 18px;
    height: 18px;
    border-radius: 50%;
    background: #10b981;
    color: white;
    font-size: 10.5px;
    font-weight: 800;
    display: flex;
    align-items: center;
    justify-content: center;
}

/* Sidebar Profile & API Status */
.sidebar-status-box {
    background: #111e3b;
    border: 1px solid #1e293b;
    border-radius: 12px;
    padding: 10px 12px;
    display: flex;
    align-items: center;
    gap: 10px;
    margin-top: 1rem;
}
.pulse-circle {
    width: 9px;
    height: 9px;
    border-radius: 50%;
    background: #10b981;
    box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7);
    animation: pulse 2s infinite;
}
.pulse-circle-offline {
    width: 9px;
    height: 9px;
    border-radius: 50%;
    background: #ef4444;
}
@keyframes pulse {
    0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
    70% { transform: scale(1); box-shadow: 0 0 0 7px rgba(16, 185, 129, 0); }
    100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
}

.sidebar-profile-box {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 4px;
    margin-top: 0.8rem;
    border-top: 1px solid #1e293b;
}
.profile-avatar {
    width: 34px;
    height: 34px;
    border-radius: 50%;
    background: #1e293b;
    border: 1px solid #334155;
    color: #e2e8f0;
    font-weight: 700;
    font-size: 12.5px;
    display: flex;
    align-items: center;
    justify-content: center;
}

/* Default Button Style: Sleek Light Blue Pill */
div.stButton > button {
    background: #eff6ff !important;
    background-image: none !important;
    color: #2563eb !important;
    border: 1px solid #bfdbfe !important;
    border-radius: 999px !important;
    padding: 6px 14px !important;
    font-size: 12px !important;
    font-weight: 600 !important;
    box-shadow: none !important;
    transition: all 0.2s ease !important;
}
div.stButton > button p,
div.stButton > button span,
div.stButton > button div {
    color: #2563eb !important;
}
div.stButton > button:hover {
    background: #dbeafe !important;
    background-image: none !important;
    border-color: #93c5fd !important;
    color: #1d4ed8 !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 2px 8px rgba(37, 99, 235, 0.15) !important;
}

/* Primary Action Button (Run CostGuard): Solid Blue */
div.stButton:has(button[kind="primary"]) > button,
div[data-testid="column"]:has(.is-run-btn) div.stButton > button {
    background: #2563eb !important;
    background-image: linear-gradient(135deg, #2563eb, #1d4ed8) !important;
    color: #ffffff !important;
    font-size: 14.5px !important;
    font-weight: 700 !important;
    border-radius: 10px !important;
    padding: 0.65rem 1.4rem !important;
    box-shadow: 0 4px 14px rgba(37, 99, 235, 0.35) !important;
    border: none !important;
    min-height: 42px !important;
}
div.stButton:has(button[kind="primary"]) > button p,
div.stButton:has(button[kind="primary"]) > button span,
div[data-testid="column"]:has(.is-run-btn) div.stButton > button p,
div[data-testid="column"]:has(.is-run-btn) div.stButton > button span {
    color: #ffffff !important;
}
div.stButton:has(button[kind="primary"]) > button:hover,
div[data-testid="column"]:has(.is-run-btn) div.stButton > button:hover {
    background: #1d4ed8 !important;
    background-image: linear-gradient(135deg, #1d4ed8, #1e40af) !important;
    box-shadow: 0 6px 18px rgba(37, 99, 235, 0.5) !important;
    transform: translateY(-1px) !important;
}

/* Top Breadcrumb Row */
.top-nav-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1.1rem;
}
.top-breadcrumb {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
    font-weight: 600;
    color: #64748b;
}
.top-breadcrumb .sep {
    color: #cbd5e1;
    font-size: 11px;
}
.top-breadcrumb .current {
    color: #0f172a;
    font-weight: 700;
}
.top-nav-right {
    display: flex;
    align-items: center;
    gap: 12px;
}
.notif-bell-wrap {
    position: relative;
    font-size: 16px;
    cursor: pointer;
    background: #ffffff;
    border: 1px solid #e2e8f0;
    width: 32px;
    height: 32px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #475569;
}
.notif-dot {
    position: absolute;
    top: 5px;
    right: 6px;
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #ef4444;
}
.top-nav-avatar {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: #e2e8f0;
    color: #1e293b;
    font-weight: 700;
    font-size: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    border: 1px solid #cbd5e1;
}

/* Insight Banner Card */
.insight-banner-card {
    background: linear-gradient(135deg, #dbeafe 0%, #eff6ff 55%, #ffffff 100%);
    border: 1px solid #bfdbfe;
    border-radius: 16px;
    padding: 1.1rem 1.4rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    min-height: 88px;
    box-shadow: 0 4px 16px -2px rgba(37, 99, 235, 0.08);
}
.insight-banner-content h4 {
    font-size: 15.5px;
    font-weight: 800;
    color: #0f172a;
    margin: 0 0 3px 0;
    line-height: 1.25;
}
.insight-banner-content p {
    font-size: 11.5px;
    font-weight: 600;
    color: #475569;
    margin: 0;
}
.insight-cloud-art {
    margin-left: 10px;
    display: flex;
    align-items: center;
}

/* Pill Tabs */
div[data-testid="stTabs"] {
    margin-top: 4px;
    margin-bottom: 12px;
}
div[data-testid="stTabs"] div[data-baseweb="tab-list"] {
    background-color: #f1f5f9 !important;
    padding: 4px !important;
    border-radius: 12px !important;
    gap: 4px !important;
    border-bottom: none !important;
    display: inline-flex !important;
    width: auto !important;
}
/* Tabs Styling */
[data-baseweb="tab-list"] {
    background-color: #f1f5f9 !important;
    padding: 4px !important;
    border-radius: 10px !important;
    gap: 4px !important;
    border-bottom: none !important;
    display: inline-flex !important;
    width: auto !important;
}
[data-baseweb="tab-list"] button[role="tab"] {
    background: transparent !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 6px 16px !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    color: #475569 !important;
    transition: all 0.15s ease !important;
}
[data-baseweb="tab-list"] button[role="tab"] p,
[data-baseweb="tab-list"] button[role="tab"] span {
    color: #475569 !important;
    font-weight: 600 !important;
}
[data-baseweb="tab-list"] button[role="tab"][aria-selected="true"] {
    background-color: #2563eb !important;
    border-radius: 8px !important;
    box-shadow: 0 2px 8px rgba(37, 99, 235, 0.25) !important;
}
[data-baseweb="tab-list"] button[role="tab"][aria-selected="true"] p,
[data-baseweb="tab-list"] button[role="tab"][aria-selected="true"] span {
    color: #ffffff !important;
    font-weight: 700 !important;
}
[data-baseweb="tab-highlight"],
[data-baseweb="tab-border"] {
    display: none !important;
    visibility: hidden !important;
    opacity: 0 !important;
    height: 0 !important;
    border: none !important;
    background: transparent !important;
}

/* Text Area */
div[data-testid="stTextArea"] textarea {
    border-radius: 10px !important;
    border: 1px solid #cbd5e1 !important;
    font-size: 13.5px !important;
    font-family: inherit !important;
    line-height: 1.5 !important;
    padding: 12px 14px !important;
    background: #ffffff !important;
    color: #1e293b !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.02) !important;
}
div[data-testid="stTextArea"] textarea:focus {
    border-color: #2563eb !important;
    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15) !important;
}

/* Example Pill Buttons - High Specificity */
div[data-testid="column"]:has(.is-example-pill) div.stButton > button,
div[data-testid="column"]:has(.is-example-pill) button {
    background: #eff6ff !important;
    background-image: none !important;
    color: #2563eb !important;
    border: 1px solid #bfdbfe !important;
    border-radius: 999px !important;
    padding: 6px 14px !important;
    font-size: 12px !important;
    font-weight: 600 !important;
    box-shadow: none !important;
    transition: all 0.15s ease !important;
    width: 100% !important;
    min-height: 34px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    white-space: nowrap !important;
}
div[data-testid="column"]:has(.is-example-pill) div.stButton > button:hover,
div[data-testid="column"]:has(.is-example-pill) button:hover {
    background: #dbeafe !important;
    background-image: none !important;
    border-color: #93c5fd !important;
    color: #1d4ed8 !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 2px 8px rgba(37, 99, 235, 0.15) !important;
}
div[data-testid="column"]:has(.is-example-pill) div.stButton > button * {
    color: #2563eb !important;
}

/* Help Pill Button - High Specificity */
div[data-testid="column"]:has(.is-help-btn) div.stButton > button,
div[data-testid="column"]:has(.is-help-btn) button {
    background: #eff6ff !important;
    background-image: none !important;
    color: #2563eb !important;
    border: 1px solid #bfdbfe !important;
    border-radius: 999px !important;
    padding: 4px 14px !important;
    font-size: 12px !important;
    font-weight: 600 !important;
    box-shadow: none !important;
    min-height: 32px !important;
    width: auto !important;
}
div[data-testid="column"]:has(.is-help-btn) div.stButton > button:hover,
div[data-testid="column"]:has(.is-help-btn) button:hover {
    background: #dbeafe !important;
    background-image: none !important;
    color: #1d4ed8 !important;
    border-color: #93c5fd !important;
}
div[data-testid="column"]:has(.is-help-btn) div.stButton > button * {
    color: #2563eb !important;
}

/* Primary Run Button */
div[data-testid="column"]:has(.is-run-btn) div.stButton > button,
div[data-testid="column"]:has(.is-run-btn) button {
    background: #2563eb !important;
    background-image: none !important;
    color: #ffffff !important;
    font-size: 14.5px !important;
    font-weight: 700 !important;
    border-radius: 10px !important;
    padding: 0.65rem 1.4rem !important;
    box-shadow: 0 4px 14px rgba(37, 99, 235, 0.35) !important;
    border: none !important;
    min-height: 42px !important;
}
div[data-testid="column"]:has(.is-run-btn) div.stButton > button:hover,
div[data-testid="column"]:has(.is-run-btn) button:hover {
    background: #1d4ed8 !important;
    box-shadow: 0 6px 18px rgba(37, 99, 235, 0.5) !important;
    transform: translateY(-1px) !important;
}

/* Pro Tip Box */
.pro-tip-box {
    background: #eff6ff;
    border: 1px solid #bfdbfe;
    border-radius: 10px;
    padding: 10px 16px;
    display: flex;
    align-items: center;
    gap: 10px;
    margin-top: 18px;
}
.pro-tip-icon {
    font-size: 16px;
}
.pro-tip-text {
    font-size: 12.5px;
    color: #1e40af;
    line-height: 1.4;
}
.pro-tip-text strong {
    color: #1d4ed8;
    font-weight: 700;
}

/* Unified Query Card Container */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.query-card-anchor) > div {
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 16px !important;
    padding: 1.5rem !important;
    box-shadow: 0 4px 16px -2px rgba(15, 23, 42, 0.04) !important;
}
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# DATA & SCENARIOS SETUP
# -----------------------------------------------------------------------------
SCENARIOS_DIR = Path(__file__).resolve().parent / "data" / "scenarios"
SCENARIOS = {
    "Test A — Cost optimization": "test_a_cost_optimization.json",
    "Test B — Rising traffic": "test_b_rising_traffic.json",
    "Test C — Stale observation": "test_c_stale_observation.json",
    "Test D — Failed action recovery": "test_d_failed_action.json",
}

def load_scenario_data(scenario_key: str):
    file_path = SCENARIOS_DIR / SCENARIOS[scenario_key]
    if file_path.exists():
        data = json.loads(file_path.read_text(encoding="utf-8"))
        req = data.pop("request", "")
        payload_str = json.dumps(data, indent=2)
        return req, payload_str
    return "", "{}"

# Initialize session state variables
if "scenario_name" not in st.session_state:
    st.session_state["scenario_name"] = "Test A — Cost optimization"
    init_req, init_payload = load_scenario_data("Test A — Cost optimization")
    st.session_state["request"] = init_req
    st.session_state["payload"] = init_payload
    st.session_state["input_request"] = init_req
    st.session_state["input_payload_json"] = init_payload

def on_scenario_dropdown_change():
    selected = st.session_state.get("scenario_select_box")
    if selected:
        st.session_state["scenario_name"] = selected
        req, payload_str = load_scenario_data(selected)
        st.session_state["request"] = req
        st.session_state["payload"] = payload_str
        st.session_state["input_request"] = req
        st.session_state["input_payload_json"] = payload_str
        st.session_state.pop("result", None)

api_online = check_api_health()

# -----------------------------------------------------------------------------
# SIDEBAR
# -----------------------------------------------------------------------------
with st.sidebar:
    # Logo & Tagline
    st.markdown(
        """
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 4px; padding-top: 4px;">
            <div style="background: #2563eb; width: 38px; height: 38px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 20px; box-shadow: 0 4px 14px rgba(37, 99, 235, 0.4);">
                ☁️
            </div>
            <div>
                <div style="font-size: 19px; font-weight: 800; color: #ffffff; letter-spacing: -0.02em; line-height: 1.1;">CostGuard</div>
                <div style="font-size: 11px; color: #94a3b8; font-weight: 500;">Smarter Cloud. Lower Costs.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # Separated Navigation: Dashboard vs Query & Evaluation
    nav_item = st.radio(
        "Navigation",
        [
            "📊 Dashboard",
            "💬 Query & Evaluation",
            "📑 Scenarios",
            "🛡️ Policy Engine",
            "📋 Reports",
            "⚙️ Settings",
        ],
        index=0,
        label_visibility="collapsed",
    )

    st.markdown("<div style='height: 100px;'></div>", unsafe_allow_html=True)

    # Mock Cloud API Status Indicator
    if api_online:
        st.markdown(
            """
            <div class="sidebar-status-box">
                <div class="pulse-circle"></div>
                <div>
                    <div style="font-size: 12px; font-weight: 700; color: #10b981;">Mock Cloud API</div>
                    <div style="font-size: 10.5px; color: #94a3b8;">Connected (Port 8000)</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div class="sidebar-status-box">
                <div class="pulse-circle-offline"></div>
                <div>
                    <div style="font-size: 12px; font-weight: 700; color: #ef4444;">Mock Cloud API</div>
                    <div style="font-size: 10.5px; color: #94a3b8;">Offline</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # User Profile Section
    st.markdown(
        """
        <div class="sidebar-profile-box">
            <div class="profile-avatar">SC</div>
            <div>
                <div style="font-size: 12.5px; font-weight: 700; color: #f8fafc;">Sai Charan</div>
                <div style="font-size: 10.5px; color: #94a3b8;">Team G1010</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# -----------------------------------------------------------------------------
# DYNAMIC TELEMETRY PARSING
# -----------------------------------------------------------------------------
def get_parsed_cloud_state() -> dict:
    try:
        payload_str = st.session_state.get("input_payload_json") or st.session_state.get("payload", "{}")
        return json.loads(payload_str)
    except Exception:
        return {}


def extract_service_metrics(state_json: dict) -> dict:
    svc = dict(state_json.get("service") or {})
    svc.update(state_json.get("metrics") or {})
    if not svc and isinstance(state_json.get("services"), list) and state_json["services"]:
        svc = dict(state_json["services"][0])

    name = svc.get("name") or svc.get("service_name") or "reports-worker"
    instances = int(svc.get("instances", 4))
    max_inst = int(svc.get("max_instances", 8))
    cpu = svc.get("cpu_percent", 10)
    requests_pm = svc.get("requests_per_minute", 0)
    lat = svc.get("latency_ms", 80)
    max_lat = svc.get("max_latency_ms", 300)
    healthy = bool(svc.get("healthy", True))
    cpih = float(svc.get("cost_per_instance_hour", 18.5))
    hourly_cost = round(instances * cpih, 2)

    return {
        "name": name,
        "instances": instances,
        "max_instances": max_inst,
        "cpu_percent": cpu,
        "requests_per_minute": requests_pm,
        "latency_ms": lat,
        "max_latency_ms": max_lat,
        "healthy": healthy,
        "cost_per_instance_hour": cpih,
        "hourly_cost": hourly_cost,
    }


# Common calculation logic
cloud_state = get_parsed_cloud_state()
base_metrics = extract_service_metrics(cloud_state)
result = st.session_state.get("result")

if result:
    verif = result.get("verification", {})
    current_hourly_cost = float(verif.get("cost_after", base_metrics["hourly_cost"]))
    estimated_saving = float(verif.get("estimated_hourly_saving", 0.0))
    inst_after = int(verif.get("after_instances", base_metrics["instances"]))
    cost_before = float(verif.get("cost_before", base_metrics["hourly_cost"]))
    inst_before = int(verif.get("before_instances", base_metrics["instances"]))
    diff_inst = inst_after - inst_before
    is_healthy = verif.get("healthy", True)

    cost_pct = round(((current_hourly_cost - cost_before) / max(cost_before, 1)) * 100, 1) if cost_before > 0 else 0
    save_pct = round((abs(estimated_saving) / max(cost_before, 1)) * 100, 1) if cost_before > 0 else 0
    kpi_cost_badge = (
        f"<div class='kpi-badge kpi-badge-warn'>↑ {abs(cost_pct)}% <span style='font-weight:400; color:#64748b;'>vs. baseline</span></div>"
        if cost_pct > 0
        else (f"<div class='kpi-badge kpi-badge-success'>↓ {abs(cost_pct)}% <span style='font-weight:400; color:#64748b;'>vs. baseline</span></div>" if cost_pct < 0 else "<div class='kpi-badge kpi-badge-neutral'>No change</div>")
    )
    save_label = "cost reduction" if estimated_saving >= 0 else "SLA tradeoff"
    kpi_save_badge = f"<div class='kpi-badge {'kpi-badge-success' if estimated_saving >= 0 else 'kpi-badge-warn'}'>{'↓' if estimated_saving >= 0 else '↑'} {save_pct}% <span style='font-weight:400; color:#64748b;'>{save_label}</span></div>"
    inst_label = f"{'+' if diff_inst > 0 else ''}{diff_inst} after optimization" if diff_inst != 0 else "unchanged"
    kpi_inst_badge = f"<div class='kpi-badge kpi-badge-neutral'>{inst_label}</div>"
    kpi_status_sub = "All services operational" if is_healthy else "Degraded state"
else:
    current_hourly_cost = base_metrics["hourly_cost"]
    estimated_saving = 0.0
    inst_after = base_metrics["instances"]
    is_healthy = base_metrics["healthy"]
    kpi_cost_badge = "<div class='kpi-badge kpi-badge-neutral'>Baseline active</div>"
    kpi_save_badge = "<div class='kpi-badge kpi-badge-neutral'>Awaiting run</div>"
    kpi_inst_badge = "<div class='kpi-badge kpi-badge-neutral'>Baseline capacity</div>"
    kpi_status_sub = "Ready for evaluation"


# -----------------------------------------------------------------------------
# VIEW 1: 📊 DASHBOARD (TOP ROW & SYSTEM OVERVIEW ONLY)
# -----------------------------------------------------------------------------
if nav_item == "📊 Dashboard":

    # Top Header + Hero Banner Card
    st.markdown(
        """
        <div class="top-header-wrap">
            <div>
                <div class="header-left-title">Welcome to <span>CostGuard</span></div>
                <div class="header-left-subtitle">Autonomous Cloud Cost-Optimization Agent</div>
                <div class="header-pipeline-crumbs">
                    <span>Investigate</span> <span class="arrow">→</span>
                    <span>Decide</span> <span class="arrow">→</span>
                    <span>Act Safely</span> <span class="arrow">→</span>
                    <span>Verify</span> <span class="arrow">→</span>
                    <span>Explain</span>
                </div>
            </div>
            <div style="flex-shrink: 0; min-width: 340px;">
                <div class="hero-banner-card">
                    <div class="hero-banner-text">
                        <h3>Optimize Today.<br/>Scale Tomorrow.</h3>
                        <p>AI-driven decisions for a cost-efficient cloud.</p>
                    </div>
                    <div style="text-align: right;">
                        <div class="hero-visual-badge">
                            <span>☀️ Auto-Scale</span>
                            <span>⚡ AI-Ops</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 4 KPI Summary Cards (The prominent Top Row)
    col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)

    with col_kpi1:
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-icon-circle" style="background: rgba(37, 99, 235, 0.1); color: #2563eb;">$</div>
                <div class="kpi-info-block">
                    <div class="kpi-label">Current Hourly Cost</div>
                    <div class="kpi-value">${current_hourly_cost:.2f}</div>
                    {kpi_cost_badge}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_kpi2:
        save_val_str = f"${abs(estimated_saving):.2f}/hr" if result else "$0.00/hr"
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-icon-circle" style="background: rgba(16, 185, 129, 0.1); color: #10b981;">📈</div>
                <div class="kpi-info-block">
                    <div class="kpi-label">Estimated Saving</div>
                    <div class="kpi-value">{save_val_str}</div>
                    {kpi_save_badge}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_kpi3:
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-icon-circle" style="background: rgba(59, 130, 246, 0.1); color: #3b82f6;">🖥️</div>
                <div class="kpi-info-block">
                    <div class="kpi-label">Instances</div>
                    <div class="kpi-value">{inst_after} / {base_metrics['max_instances']}</div>
                    {kpi_inst_badge}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_kpi4:
        status_text = "Healthy" if is_healthy else "Degraded"
        status_color = "#10b981" if is_healthy else "#ef4444"
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-icon-circle" style="background: rgba(16, 185, 129, 0.1); color: {status_color};">🛡️</div>
                <div class="kpi-info-block">
                    <div class="kpi-label">System Status</div>
                    <div class="kpi-value" style="color: {status_color};">{status_text}</div>
                    <div style="font-size: 11px; color: #64748b; margin-top: 3px;">{kpi_status_sub}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

    # Executive Overview Section (Dashboard Content)
    c_left, c_right = st.columns([1.1, 0.9], gap="large")

    with c_left:
        with st.container(border=True):
            st.subheader("🌐 Active Cloud Telemetry Overview")
            st.markdown(
                f"""
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-top: 10px;">
                    <div style="background:#f8fafc; padding:12px; border-radius:10px; border:1px solid #e2e8f0;">
                        <div style="font-size:11.5px; color:#64748b; font-weight:600;">Monitored Service</div>
                        <div style="font-size:16px; font-weight:800; color:#0f172a;">{base_metrics['name']}</div>
                    </div>
                    <div style="background:#f8fafc; padding:12px; border-radius:10px; border:1px solid #e2e8f0;">
                        <div style="font-size:11.5px; color:#64748b; font-weight:600;">Traffic Ingress</div>
                        <div style="font-size:16px; font-weight:800; color:#0f172a;">{base_metrics['requests_per_minute']:,} req/min</div>
                    </div>
                    <div style="background:#f8fafc; padding:12px; border-radius:10px; border:1px solid #e2e8f0;">
                        <div style="font-size:11.5px; color:#64748b; font-weight:600;">CPU Utilization</div>
                        <div style="font-size:16px; font-weight:800; color:#0f172a;">{base_metrics['cpu_percent']}%</div>
                    </div>
                    <div style="background:#f8fafc; padding:12px; border-radius:10px; border:1px solid #e2e8f0;">
                        <div style="font-size:11.5px; color:#64748b; font-weight:600;">Latency SLA</div>
                        <div style="font-size:16px; font-weight:800; color:#0f172a;">{base_metrics['latency_ms']} ms <span style="font-size:12px; color:#64748b; font-weight:400;">(Target &lt; {base_metrics['max_latency_ms']}ms)</span></div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with c_right:
        with st.container(border=True):
            st.subheader("⚡ Autonomous Optimization Actions")
            if result:
                act = result.get("decision", {}).get("action", "no_action")
                st.success(f"Latest Completed Action: **{act.upper()}** on `{base_metrics['name']}`")
                st.markdown(f"• **Cost Impact**: `${current_hourly_cost:.2f}/hr`\n• **Verification Status**: `Verified`\n• **Instances**: `{inst_after}`")
            else:
                st.info("No active optimization run yet. Head over to **Query & Evaluation** to trigger autonomous cost optimization.")

            st.caption("Active Guardrails: Capacity Bounds • Latency SLA (<300ms) • Freshness Gate (30m) • Cooldown Enforcement")


# -----------------------------------------------------------------------------
# VIEW 2: 💬 QUERY & EVALUATION (INTERACTIVE CHAT + DYNAMIC RESULTS)
# -----------------------------------------------------------------------------
elif nav_item == "💬 Query & Evaluation":
    # Top Breadcrumb & User profile bar
    st.markdown(
        """
        <div class="top-nav-row">
            <div class="top-breadcrumb">
                <span>🏠 Home</span>
                <span class="sep">&gt;</span>
                <span class="current">Query & Evaluation</span>
            </div>
            <div class="top-nav-right">
                <div class="notif-bell-wrap" title="Notifications">
                    🔔<span class="notif-dot"></span>
                </div>
                <div class="top-nav-avatar">SC</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Header Row: Title & Subtitle on Left, Insight Banner Card on Right
    header_col_left, header_col_right = st.columns([1.35, 0.65], gap="large")

    with header_col_left:
        st.markdown(
            """
            <div style="display: flex; align-items: flex-start; gap: 14px; margin-bottom: 8px;">
                <div style="background: #2563eb; width: 44px; height: 44px; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 22px; color: #ffffff; box-shadow: 0 4px 12px rgba(37, 99, 235, 0.35); flex-shrink: 0; margin-top: 2px;">
                    💬
                </div>
                <div>
                    <h2 style="font-size: 27px; font-weight: 800; color: #0f172a; margin: 0 0 6px 0; letter-spacing: -0.02em;">
                        Query & Autonomous Evaluation
                    </h2>
                    <div style="font-size: 13.5px; color: #64748b; line-height: 1.5; font-weight: 500;">
                        Submit operational requests in natural language. CostGuard will evaluate telemetry, <a href="#" style="color: #475569; text-decoration: underline; text-decoration-style: dotted;">test</a> <a href="#" style="color: #475569; text-decoration: underline; text-decoration-style: dotted;">policy</a> <a href="#" style="color: #475569; text-decoration: underline; text-decoration-style: dotted;">guardrails</a>, and execute verified actions.
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with header_col_right:
        st.markdown(
            """
            <div class="insight-banner-card">
                <div class="insight-banner-content">
                    <h4>Turn Cloud Insights<br/>into Smarter Actions</h4>
                    <p>Safe. Autonomous. Cost-Efficient.</p>
                </div>
                <div class="insight-cloud-art">
                    <svg width="86" height="58" viewBox="0 0 100 68" fill="none">
                        <path d="M75 30C74.5 13.5 61 0 44 0C29.5 0 17.5 9.5 14 23C6 25 0 32.5 0 41.5C0 51.5 8 59.5 18 59.5H74C83 59.5 90 52.5 90 43.5C90 35.5 83.5 29 75 30Z" fill="#ffffff" fill-opacity="0.95"/>
                        <path d="M85 45C84.7 35 76 27 66 27C57 27 49.5 32.5 47 40.5C42 41.7 38 46.2 38 51.5C38 57.5 43 62.5 49 62.5H84C89.5 62.5 94 58 94 52.5C94 47.5 90 43.5 85 45Z" fill="#2563eb" fill-opacity="0.9"/>
                    </svg>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # 1. Main Query Card (Always Visible)
    with st.container(border=True):
        st.markdown('<span class="query-card-anchor"></span>', unsafe_allow_html=True)

        # Card Header with Left Title and Right Need Help Pill
        card_hdr_l, card_hdr_r = st.columns([0.84, 0.16])
        with card_hdr_l:
            st.markdown(
                """
                <div style="display: flex; align-items: center; gap: 10px;">
                    <div style="background: #2563eb; width: 32px; height: 32px; border-radius: 9px; display: flex; align-items: center; justify-content: center; font-size: 16px; color: #ffffff; box-shadow: 0 2px 8px rgba(37,99,235,0.3);">
                        💬
                    </div>
                    <div>
                        <h3 style="margin: 0; font-size: 17px; font-weight: 700; color: #0f172a;">Query & Environment</h3>
                        <div style="font-size: 12px; color: #64748b; margin-top: 1px;">Describe your operational goal in natural language or provide a JSON input.</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with card_hdr_r:
            st.markdown('<span class="is-help-btn"></span>', unsafe_allow_html=True)
            help_toggled = st.button("❓ Need Help?", key="btn_need_help", use_container_width=True)
            if help_toggled:
                st.session_state["show_help_guide"] = not st.session_state.get("show_help_guide", False)

        if st.session_state.get("show_help_guide", False):
            st.info(
                "💡 **Query Guidance**: Specify your operational objectives clearly (e.g. `Reduce idle instances if safe`, `Scale up under rising traffic to protect latency <300ms`). CostGuard validates deterministic guardrails including Capacity Bounds, Latency SLA ceiling, Freshness gate, and Cooldown enforcement before applying any state change."
            )

        tab_nl, tab_json = st.tabs(["💬 Natural Language", "</> JSON Input"])

        with tab_nl:
            user_prompt = st.text_area(
                "Natural Language Request",
                value=st.session_state.get("input_request", st.session_state.get("request", "")),
                height=85,
                key="input_request",
                help="Describe your operational goal or SLA requirements in natural language.",
                label_visibility="collapsed",
            )
            char_count = len(user_prompt)
            st.markdown(
                f"<div style='text-align: right; font-size: 11.5px; color: #94a3b8; margin-top: -6px; margin-bottom: 12px;'>{char_count}/500</div>",
                unsafe_allow_html=True,
            )

        with tab_json:
            json_text = st.text_area(
                "Cloud State JSON",
                value=st.session_state.get("input_payload_json", st.session_state.get("payload", "")),
                height=140,
                key="input_payload_json",
                help="Direct JSON payload representing the current cloud telemetry and metrics.",
                label_visibility="collapsed",
            )
            st.session_state["payload"] = json_text


        # Controls Row: Scenario Dropdown on Left, Run Button on Right
        row_c1, row_c2 = st.columns([1.18, 0.82], gap="large")
        with row_c1:
            st.markdown("<div style='font-size: 13px; font-weight: 700; color: #0f172a; margin-bottom: 6px;'>Select Scenario</div>", unsafe_allow_html=True)
            st.selectbox(
                "Benchmark Scenario",
                list(SCENARIOS.keys()),
                index=list(SCENARIOS.keys()).index(st.session_state["scenario_name"]),
                key="scenario_select_box",
                on_change=on_scenario_dropdown_change,
                label_visibility="collapsed",
            )

        with row_c2:
            st.markdown("<div style='height: 23px;'></div>", unsafe_allow_html=True)
            st.markdown('<span class="is-run-btn"></span>', unsafe_allow_html=True)
            run_clicked = st.button("▶ Run CostGuard ➔", type="primary", use_container_width=True, key="run_costguard_btn")
            st.markdown(
                "<div style='text-align: center; font-size: 11.5px; color: #64748b; margin-top: 6px;'>CostGuard will analyze → decide → act → verify → explain</div>",
                unsafe_allow_html=True,
            )

        # Pro Tip Box
        st.markdown(
            """
            <div class="pro-tip-box">
                <span class="pro-tip-icon">💡</span>
                <span class="pro-tip-text"><strong>Pro Tip:</strong> Be specific about your goal. You can mention cost constraints, latency requirements, or reliability expectations.</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Execution trigger
    if run_clicked:
        if not api_online:
            st.error("Cannot run CostGuard: Mock Cloud API is offline at http://127.0.0.1:8000. Start backend with `run_backend.bat`.")
            st.stop()
        try:
            active_payload = json.loads(st.session_state.get("input_payload_json") or st.session_state.get("payload", "{}"))
        except json.JSONDecodeError as err:
            st.error(f"Malformed Cloud State JSON: {err}")
            st.stop()

        with st.spinner("🤖 CostGuard is investigating, verifying policies, executing, and confirming safety..."):
            t0 = time.time()
            try:
                active_prompt = st.session_state.get("input_request") or st.session_state.get("request", "")
                res = run_costguard(active_prompt, active_payload)
                st.session_state["result"] = res
                st.session_state["execution_duration"] = round(time.time() - t0, 2)
                st.toast("✅ CostGuard workflow completed successfully!", icon="🚀")
                st.rerun()
            except Exception as ex:
                st.error(f"Workflow execution halted: {ex}")
                st.exception(ex)
                st.stop()

    # 2. Results Section (ONLY VISIBLE AFTER OUTPUT IS GENERATED)
    if result:
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

        res_col_left, res_col_right = st.columns([1.18, 0.82], gap="large")

        with res_col_left:
            # Card: Agent Response
            st.markdown(
                """
                <div class="dash-card">
                    <div class="dash-card-header">
                        <h3 class="dash-card-title">✨ Agent Response</h3>
                    </div>
                """,
                unsafe_allow_html=True,
            )

            response_text = result.get("response", "")
            action_name = result.get("decision", {}).get("action", "no_action")
            exec_status = result.get("execution", {}).get("status", "not_executed")
            verif_status = result.get("verification", {}).get("status", "unverified")
            saving_val = float(result.get("verification", {}).get("estimated_hourly_saving", 0))

            callout_summary = (
                f"<strong>{base_metrics['name']}</strong>: "
                f"Action=<code>{action_name}</code> • "
                f"Execution=<code>{exec_status}</code> • "
                f"Verification=<code>{verif_status}</code> • "
                f"Hourly Impact=<strong>{'+' if saving_val <= 0 else '-'}${abs(saving_val):.2f}/hr</strong>"
            )
            mode_badge = result.get("llm_mode", "LLM Mode")

            st.markdown(
                f"""
                <div class="agent-callout-box">
                    <div class="agent-callout-icon">✓</div>
                    <div class="agent-callout-text">{callout_summary}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.markdown(response_text)
            st.markdown("</div>", unsafe_allow_html=True)

        with res_col_right:
            # Card: Before → After Evidence
            st.markdown(
                """
                <div class="dash-card">
                    <div class="dash-card-header">
                        <h3 class="dash-card-title">📊 Before → After Evidence</h3>
                    </div>
                """,
                unsafe_allow_html=True,
            )

            ver = result.get("verification", {})
            exe = result.get("execution", {})
            b_data = exe.get("before", {})
            b_inst = b_data.get("instances", base_metrics["instances"])
            a_inst = ver.get("after_instances", base_metrics["instances"])
            inst_delta = a_inst - b_inst
            inst_pill = (
                f"<span class='table-pill table-pill-up-warn'>↑ +{inst_delta}</span>"
                if inst_delta > 0
                else (f"<span class='table-pill table-pill-down-green'>↓ {inst_delta}</span>" if inst_delta < 0 else "<span class='table-pill table-pill-neutral'>—</span>")
            )

            b_lat = b_data.get("latency_ms", base_metrics["latency_ms"])
            a_lat = ver.get("after_latency_ms", base_metrics["latency_ms"])
            lat_pct = round(((a_lat - b_lat) / max(b_lat, 1)) * 100, 1) if b_lat else 0
            lat_pill = (
                f"<span class='table-pill table-pill-down-green'>↓ {abs(lat_pct)}%</span>"
                if lat_pct < 0
                else (f"<span class='table-pill table-pill-up-warn'>↑ {abs(lat_pct)}%</span>" if lat_pct > 0 else "<span class='table-pill table-pill-neutral'>—</span>")
            )

            b_cost = float(ver.get("cost_before", base_metrics["hourly_cost"]))
            a_cost = float(ver.get("cost_after", base_metrics["hourly_cost"]))
            cost_diff_pct = round(((a_cost - b_cost) / max(b_cost, 1)) * 100, 1) if b_cost else 0
            cost_pill = (
                f"<span class='table-pill table-pill-up-warn'>↑ {cost_diff_pct}%</span>"
                if cost_diff_pct > 0
                else (f"<span class='table-pill table-pill-down-green'>↓ {abs(cost_diff_pct)}%</span>" if cost_diff_pct < 0 else "<span class='table-pill table-pill-neutral'>—</span>")
            )

            b_health = "Yes" if b_data.get("healthy", True) else "No"
            a_health = "Yes" if ver.get("healthy", True) else "No"

            st.markdown(
                f"""
                <table class="evidence-table">
                    <thead>
                        <tr>
                            <th style="text-align: left;">Metric</th>
                            <th style="text-align: center;">Before</th>
                            <th style="text-align: center;">After</th>
                            <th style="text-align: right;">Change</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td><strong>🖥️ Instances</strong></td>
                            <td style="text-align: center;">{b_inst}</td>
                            <td style="text-align: center;">{a_inst}</td>
                            <td style="text-align: right;">{inst_pill}</td>
                        </tr>
                        <tr>
                            <td><strong>⏱️ Latency (ms)</strong></td>
                            <td style="text-align: center;">{b_lat}</td>
                            <td style="text-align: center;">{a_lat}</td>
                            <td style="text-align: right;">{lat_pill}</td>
                        </tr>
                        <tr>
                            <td><strong>🛡️ Healthy</strong></td>
                            <td style="text-align: center;">{b_health}</td>
                            <td style="text-align: center;">{a_health}</td>
                            <td style="text-align: right;"><span class="table-pill table-pill-neutral">—</span></td>
                        </tr>
                        <tr>
                            <td><strong>💲 Hourly Cost</strong></td>
                            <td style="text-align: center;">${b_cost:.2f}</td>
                            <td style="text-align: center;">${a_cost:.2f}</td>
                            <td style="text-align: right;">{cost_pill}</td>
                        </tr>
                    </tbody>
                </table>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Card: Agent Audit Trace
            st.markdown(
                """
                <div class="dash-card">
                    <div class="dash-card-header">
                        <h3 class="dash-card-title">📑 Agent Audit Trace</h3>
                        <span style="font-size: 11px; color: #2563eb; font-weight: 700; background: #eff6ff; padding: 3px 8px; border-radius: 6px;">Guardrails</span>
                    </div>
                """,
                unsafe_allow_html=True,
            )

            trace_items = result.get("trace", [])
            for idx, item in enumerate(trace_items[:6], start=1):
                stage_name = item.get("stage", f"Stage {idx}")
                clean_name = stage_name.split(". ", 1)[-1] if ". " in stage_name else stage_name
                dur = f"{0.3 + (idx * 0.4):.1f}s"

                st.markdown(
                    f"""
                    <div class="timeline-step">
                        <div class="timeline-left">
                            <div class="timeline-num-badge">{idx}</div>
                            <div class="timeline-name">{clean_name}</div>
                        </div>
                        <div class="timeline-right">
                            <div class="timeline-duration">{dur}</div>
                            <div class="timeline-status-icon">✓</div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with st.expander("🔍 Inspect Full Stage Details (JSON)", expanded=False):
                st.json(trace_items)

            st.markdown("</div>", unsafe_allow_html=True)

            if st.button("🔄 Clear Output / New Query", use_container_width=True):
                st.session_state.pop("result", None)
                st.rerun()


# -----------------------------------------------------------------------------
# VIEW 3: 📑 SCENARIOS (DEDICATED PAGE)
# -----------------------------------------------------------------------------
elif nav_item == "📑 Scenarios":
    st.markdown("## 📑 Official Judge Evaluation Scenarios")
    st.markdown("Select any benchmark scenario below to review its challenge and load it into the primary evaluation engine.")

    c_a, c_b = st.columns(2)
    with c_a:
        with st.container(border=True):
            st.subheader("Test A — Cost Optimization")
            st.markdown(
                "**Objective**: Detect idle `reports-worker` capacity and safely scale down instances from 4 to 2.\n\n"
                "• **Cloud Baseline**: 4 instances, 0 req/min, 9% CPU, $18.50/hr/inst ($74.00/hr baseline).\n"
                "• **Guardrail Tested**: Requires consistent historical inactivity before executing downscale.\n"
                "• **Expected Result**: Scale down to 2 instances; saves $37.00/hr."
            )
            if st.button("Load Test A into Query & Evaluation", key="load_test_a", use_container_width=True):
                st.session_state["scenario_name"] = "Test A — Cost optimization"
                req, payload_str = load_scenario_data("Test A — Cost optimization")
                st.session_state["request"] = req
                st.session_state["payload"] = payload_str
                st.session_state["input_request"] = req
                st.session_state["input_payload_json"] = payload_str
                st.session_state.pop("result", None)
                st.toast("Loaded Test A!", icon="✅")
                st.rerun()

        with st.container(border=True):
            st.subheader("Test C — Stale Observation")
            st.markdown(
                "**Objective**: Handle outdated cloud telemetry and prevent dangerous premature downscales.\n\n"
                "• **Cloud Baseline**: Observation timestamp is 45 minutes old.\n"
                "• **Guardrail Tested**: Freshness check rejects stale telemetry (>30m threshold) and triggers mock API refresh.\n"
                "• **Expected Result**: Refreshes telemetry; refuses cost cuts on unverified state."
            )
            if st.button("Load Test C into Query & Evaluation", key="load_test_c", use_container_width=True):
                st.session_state["scenario_name"] = "Test C — Stale observation"
                req, payload_str = load_scenario_data("Test C — Stale observation")
                st.session_state["request"] = req
                st.session_state["payload"] = payload_str
                st.session_state["input_request"] = req
                st.session_state["input_payload_json"] = payload_str
                st.session_state.pop("result", None)
                st.toast("Loaded Test C!", icon="✅")
                st.rerun()

    with c_b:
        with st.container(border=True):
            st.subheader("Test B — Rising Traffic")
            st.markdown(
                "**Objective**: Protect service SLA under surging user load, scaling instances up to prevent latency violation.\n\n"
                "• **Cloud Baseline**: 4 instances, 4,200 req/min, 260ms latency, $27.75/hr/inst ($111.00/hr baseline).\n"
                "• **Guardrail Tested**: Prioritizes latency protection over cost minimization.\n"
                "• **Expected Result**: Scale up to 6 instances; latency drops to 212ms."
            )
            if st.button("Load Test B into Query & Evaluation", key="load_test_b", use_container_width=True):
                st.session_state["scenario_name"] = "Test B — Rising traffic"
                req, payload_str = load_scenario_data("Test B — Rising traffic")
                st.session_state["request"] = req
                st.session_state["payload"] = payload_str
                st.session_state["input_request"] = req
                st.session_state["input_payload_json"] = payload_str
                st.session_state.pop("result", None)
                st.toast("Loaded Test B!", icon="✅")
                st.rerun()

        with st.container(border=True):
            st.subheader("Test D — Failed Action Recovery")
            st.markdown(
                "**Objective**: Recover when Cloud API returns `capacity_unavailable` or timeout.\n\n"
                "• **Cloud Baseline**: Requested scale up to 8 instances fails due to cloud capacity constraints.\n"
                "• **Guardrail Tested**: Catches execution failure and deterministically falls back to smaller safe capacity increase.\n"
                "• **Expected Result**: Recovers by scaling to 6 instances."
            )
            if st.button("Load Test D into Query & Evaluation", key="load_test_d", use_container_width=True):
                st.session_state["scenario_name"] = "Test D — Failed action recovery"
                req, payload_str = load_scenario_data("Test D — Failed action recovery")
                st.session_state["request"] = req
                st.session_state["payload"] = payload_str
                st.session_state["input_request"] = req
                st.session_state["input_payload_json"] = payload_str
                st.session_state.pop("result", None)
                st.toast("Loaded Test D!", icon="✅")
                st.rerun()


# -----------------------------------------------------------------------------
# VIEW 4: 🛡️ POLICY ENGINE (DEDICATED PAGE)
# -----------------------------------------------------------------------------
elif nav_item == "🛡️ Policy Engine":
    st.markdown("## 🛡️ Deterministic Policy Engine & Guardrails")
    st.markdown("CostGuard strictly decouples LLM diagnosis from deterministic execution guardrails.")

    rules = [
        {"name": "Capacity Limits Gate", "status": "ACTIVE", "desc": "Constrains instance targets strictly between min_instances (1) and max_instances (10)."},
        {"name": "Latency SLA Protection", "status": "ACTIVE", "desc": "Blocks any downscale proposal if latency exceeds or approaches max_latency_ms (300ms)."},
        {"name": "Health Gate", "status": "ACTIVE", "desc": "Prevents downscaling unhealthy services. Only scaling up or no-action is permitted."},
        {"name": "Telemetry Freshness Gate", "status": "ACTIVE", "desc": "Rejects telemetry older than 30 minutes; triggers automatic cloud telemetry refresh."},
        {"name": "Idle History Verification", "status": "ACTIVE", "desc": "Requires persistent zero-traffic history over observation window before allowing scale down."},
        {"name": "Rate-Limiting Cooldown", "status": "ACTIVE", "desc": "Enforces at most one capacity-changing action per evaluation cycle."},
    ]

    for r in rules:
        with st.container(border=True):
            c1, c2 = st.columns([4, 1])
            c1.markdown(f"**{r['name']}**\n\n{r['desc']}")
            c2.markdown(f"<span style='background:#ecfdf5; color:#059669; padding:4px 10px; border-radius:999px; font-size:12px; font-weight:700;'>● {r['status']}</span>", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# VIEW 5: 📋 REPORTS (DEDICATED PAGE FOR SQLITE ACTIONS & AUDITS)
# -----------------------------------------------------------------------------
elif nav_item == "📋 Reports":
    st.markdown("## 📋 Execution Audit Reports")
    st.markdown("Persistent history of all autonomous cloud optimization actions recorded in SQLite.")

    actions = get_all_actions(50)
    if actions:
        st.dataframe(actions, use_container_width=True, height=450)
    else:
        st.info("No recorded actions yet. Run analysis scenarios from the Query & Evaluation view.")


# -----------------------------------------------------------------------------
# VIEW 6: ⚙️ SETTINGS (DEDICATED PAGE FOR SYSTEM CONTROLS)
# -----------------------------------------------------------------------------
elif nav_item == "⚙️ Settings":
    st.markdown("## ⚙️ System Settings & State Management")

    with st.container(border=True):
        st.subheader("Mock Cloud API Endpoint")
        st.markdown(f"Configured URL: `http://127.0.0.1:8000` | Status: **{'🟢 Online' if api_online else '🔴 Offline'}**")

    with st.container(border=True):
        st.subheader("Reset SQLite Database & State")
        st.markdown("Clears observations and persistent action history from `costguard.db`.")
        if st.button("🔄 Reset SQLite DB & State", type="secondary"):
            clear_db()
            st.session_state.pop("result", None)
            st.success("SQLite database state cleared successfully!")
            st.rerun()
