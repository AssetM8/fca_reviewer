"""
app.py — Smart Regulatory Reviewer  |  Redesigned UI
Run with: streamlit run app.py --server.port 8501
"""

import streamlit as st
import httpx
import pandas as pd
import json
import plotly.graph_objects as go

BACKEND_URL = "http://localhost:8001"

st.set_page_config(
    layout="wide",
    page_title="Smart Regulatory Reviewer",
    page_icon="📊",
    initial_sidebar_state="expanded",
)

# ═══════════════════════════════════════════════════════════════════════════
# GLOBAL CSS
# ═══════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* ── Base ── */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}
.main .block-container {
    padding: 1.5rem 2rem 2rem;
    max-width: 1400px;
}

/* ── Hide default Streamlit chrome ── */
#MainMenu, footer, .stDeployButton { display: none !important; }
header[data-testid="stHeader"] { background: transparent; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #0F172A;
    border-right: none;
}
[data-testid="stSidebar"] * { color: #CBD5E1 !important; }
[data-testid="stSidebar"] .stFileUploader label { color: #94A3B8 !important; font-size: 0.78rem !important; }
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 { color: #F1F5F9 !important; }
[data-testid="stSidebar"] .stButton > button {
    background: #1E3A5F !important;
    color: #E2E8F0 !important;
    border: 1px solid #334155 !important;
    border-radius: 8px !important;
    width: 100%;
    font-size: 0.85rem !important;
    transition: all 0.2s ease;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: #2563EB !important;
    border-color: #2563EB !important;
    color: white !important;
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(37,99,235,0.3) !important;
}
[data-testid="stSidebar"] [data-testid="stFileUploader"] {
    background: #1E293B;
    border-radius: 10px;
    padding: 8px;
    border: 1px dashed #334155;
}

/* ── Page header ── */
.page-header {
    background: linear-gradient(135deg, #0F172A 0%, #1E3A5F 50%, #1e40af 100%);
    border-radius: 16px;
    padding: 28px 32px;
    margin-bottom: 24px;
    position: relative;
    overflow: hidden;
    animation: fadeInDown 0.5s ease;
}
.page-header::after {
    content: '';
    position: absolute;
    top: -50%; right: -10%;
    width: 300px; height: 300px;
    background: radial-gradient(circle, rgba(59,130,246,0.15) 0%, transparent 70%);
    pointer-events: none;
}
.page-header h1 {
    color: #F8FAFC !important;
    font-size: 1.6rem !important;
    font-weight: 700 !important;
    margin: 0 !important;
    letter-spacing: -0.02em;
}
.page-header p {
    color: #94A3B8 !important;
    font-size: 0.85rem;
    margin: 4px 0 0;
}
.header-badge {
    display: inline-block;
    background: rgba(37,99,235,0.25);
    border: 1px solid rgba(96,165,250,0.3);
    color: #93C5FD;
    border-radius: 20px;
    padding: 2px 12px;
    font-size: 0.72rem;
    font-weight: 500;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    margin-bottom: 8px;
}

/* ── KPI Cards ── */
.kpi-grid {
    display: grid;
    grid-template-columns: repeat(6, 1fr);
    gap: 12px;
    margin-bottom: 24px;
    animation: fadeInUp 0.4s ease 0.1s both;
}
.kpi-card {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    padding: 16px;
    position: relative;
    overflow: hidden;
    transition: all 0.25s ease;
    cursor: default;
}
.kpi-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 12px 28px rgba(0,0,0,0.09);
    border-color: #BFDBFE;
}
.kpi-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    border-radius: 12px 12px 0 0;
}
.kpi-card.blue::before   { background: #3B82F6; }
.kpi-card.slate::before  { background: #64748B; }
.kpi-card.red::before    { background: #EF4444; }
.kpi-card.amber::before  { background: #F59E0B; }
.kpi-card.orange::before { background: #F97316; }
.kpi-card.violet::before { background: #8B5CF6; }
.kpi-icon {
    font-size: 1.4rem;
    margin-bottom: 6px;
    display: block;
}
.kpi-value {
    font-size: 1.75rem;
    font-weight: 700;
    color: #0F172A;
    line-height: 1;
    margin-bottom: 4px;
}
.kpi-label {
    font-size: 0.72rem;
    color: #64748B;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}

/* ── Section headers ── */
.section-header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin: 24px 0 14px;
    animation: fadeInUp 0.3s ease both;
}
.section-header h3 {
    font-size: 0.95rem !important;
    font-weight: 600 !important;
    color: #1E293B !important;
    margin: 0 !important;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}
.section-line {
    flex: 1;
    height: 1px;
    background: linear-gradient(to right, #E2E8F0, transparent);
}

/* ── Priority badges ── */
.badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.04em;
}
.badge-high   { background: #FEE2E2; color: #991B1B; border: 1px solid #FECACA; }
.badge-medium { background: #FEF3C7; color: #92400E; border: 1px solid #FDE68A; }
.badge-low    { background: #D1FAE5; color: #065F46; border: 1px solid #A7F3D0; }
.badge-ok     { background: #DBEAFE; color: #1E40AF; border: 1px solid #BFDBFE; }

/* ── Status cards ── */
.status-card {
    background: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 10px;
    padding: 14px 16px;
    margin-bottom: 8px;
    transition: all 0.2s ease;
    animation: fadeInUp 0.3s ease both;
}
.status-card:hover { background: #F1F5F9; border-color: #CBD5E1; }
.status-card.high   { border-left: 4px solid #EF4444; }
.status-card.medium { border-left: 4px solid #F59E0B; }
.status-card.low    { border-left: 4px solid #10B981; }

/* ── Commentary bubbles ── */
.comment-bubble {
    background: #F0F9FF;
    border: 1px solid #BAE6FD;
    border-radius: 0 12px 12px 12px;
    padding: 14px 18px;
    margin: 8px 0 20px;
    font-size: 0.88rem;
    line-height: 1.6;
    color: #0C4A6E;
    position: relative;
    animation: fadeInUp 0.3s ease both;
}
.comment-bubble::before {
    content: '"';
    font-size: 2.5rem;
    color: #7DD3FC;
    position: absolute;
    top: -8px; left: 10px;
    font-family: Georgia, serif;
    line-height: 1;
}
.comment-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 10px;
}
.comment-title {
    font-weight: 600;
    color: #0F172A;
    font-size: 0.9rem;
}
.comment-metrics {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
    margin-bottom: 10px;
}
.comment-metric {
    background: white;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    padding: 8px 12px;
    text-align: center;
}
.comment-metric-val {
    font-size: 1.05rem;
    font-weight: 700;
    color: #0F172A;
}
.comment-metric-lbl {
    font-size: 0.68rem;
    color: #64748B;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

/* ── CCR Alert cards ── */
.ccr-card {
    background: white;
    border-radius: 10px;
    padding: 14px 16px;
    margin-bottom: 8px;
    border: 1px solid #E2E8F0;
    transition: all 0.2s ease;
}
.ccr-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.07); }
.ccr-card.high   { border-left: 4px solid #EF4444; background: #FFF8F8; }
.ccr-card.medium { border-left: 4px solid #F59E0B; background: #FFFBF0; }
.ccr-check-type {
    font-size: 0.68rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #64748B;
    margin-bottom: 4px;
}
.ccr-finding {
    font-size: 0.83rem;
    color: #1E293B;
    line-height: 1.5;
}

/* ── Exec summary ── */
.memo-container {
    background: white;
    border: 1px solid #E2E8F0;
    border-radius: 16px;
    padding: 36px 40px;
    box-shadow: 0 4px 24px rgba(0,0,0,0.06);
    animation: fadeInUp 0.4s ease both;
}
.memo-title {
    font-size: 1.2rem;
    font-weight: 700;
    color: #0F172A;
    margin-bottom: 4px;
}
.memo-meta {
    font-size: 0.78rem;
    color: #64748B;
    margin-bottom: 20px;
    padding-bottom: 16px;
    border-bottom: 2px solid #F1F5F9;
}
.memo-section-title {
    font-size: 0.78rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #2563EB;
    margin: 20px 0 8px;
    display: flex;
    align-items: center;
    gap: 8px;
}
.memo-section-title::after {
    content: '';
    flex: 1;
    height: 1px;
    background: #DBEAFE;
}
.memo-text {
    font-size: 0.875rem;
    color: #334155;
    line-height: 1.7;
}

/* ── Export cards ── */
.export-card {
    background: white;
    border: 1px solid #E2E8F0;
    border-radius: 14px;
    padding: 24px;
    text-align: center;
    transition: all 0.25s ease;
    cursor: pointer;
}
.export-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 16px 32px rgba(0,0,0,0.1);
    border-color: #BFDBFE;
}
.export-icon { font-size: 2.4rem; margin-bottom: 10px; display: block; }
.export-title { font-size: 0.9rem; font-weight: 600; color: #0F172A; margin-bottom: 4px; }
.export-desc  { font-size: 0.75rem; color: #64748B; line-height: 1.4; }

/* ── Upload zone ── */
.upload-zone {
    background: #F8FAFC;
    border: 2px dashed #CBD5E1;
    border-radius: 12px;
    padding: 20px;
    text-align: center;
    transition: all 0.2s ease;
    margin-bottom: 8px;
}
.upload-zone:hover { border-color: #3B82F6; background: #EFF6FF; }
.upload-label { font-size: 0.8rem; color: #64748B; margin-top: 6px; }

/* ── Tabs ── */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    background: #F8FAFC;
    border-radius: 10px;
    padding: 4px;
    gap: 2px;
    border: 1px solid #E2E8F0;
}
[data-testid="stTabs"] [data-baseweb="tab"] {
    background: transparent !important;
    border-radius: 7px !important;
    color: #64748B !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    padding: 6px 14px !important;
    transition: all 0.15s ease !important;
}
[data-testid="stTabs"] [aria-selected="true"] {
    background: white !important;
    color: #1E40AF !important;
    font-weight: 600 !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.1) !important;
}

/* ── Buttons ── */
.stButton > button {
    border-radius: 8px !important;
    font-weight: 500 !important;
    font-size: 0.85rem !important;
    transition: all 0.2s ease !important;
    border: 1px solid #E2E8F0 !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #1E40AF, #2563EB) !important;
    color: white !important;
    border: none !important;
    box-shadow: 0 2px 8px rgba(37,99,235,0.25) !important;
}
.stButton > button[kind="primary"]:hover {
    box-shadow: 0 6px 18px rgba(37,99,235,0.4) !important;
    transform: translateY(-1px) !important;
}
.stButton > button:not([kind="primary"]):hover {
    background: #F1F5F9 !important;
    border-color: #CBD5E1 !important;
    transform: translateY(-1px) !important;
}

/* ── Expanders ── */
[data-testid="stExpander"] {
    background: white !important;
    border: 1px solid #E2E8F0 !important;
    border-radius: 10px !important;
    margin-bottom: 6px !important;
    overflow: hidden;
}
[data-testid="stExpander"]:hover { border-color: #BFDBFE !important; }
[data-testid="stExpander"] summary {
    background: #FAFBFC !important;
    padding: 10px 16px !important;
    font-size: 0.85rem !important;
    font-weight: 500 !important;
    color: #1E293B !important;
}

/* ── Dataframe ── */
[data-testid="stDataFrame"] {
    border: 1px solid #E2E8F0 !important;
    border-radius: 10px !important;
    overflow: hidden;
}

/* ── Success / info / warning ── */
[data-testid="stAlert"] {
    border-radius: 10px !important;
    border: none !important;
    font-size: 0.85rem !important;
}

/* ── Animations ── */
@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(16px); }
    to   { opacity: 1; transform: translateY(0);    }
}
@keyframes fadeInDown {
    from { opacity: 0; transform: translateY(-12px); }
    to   { opacity: 1; transform: translateY(0);     }
}
@keyframes pulse {
    0%, 100% { opacity: 1;   }
    50%       { opacity: 0.6; }
}
.loading-pulse { animation: pulse 1.5s ease infinite; }

/* ── Sidebar status pill ── */
.sidebar-status {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 12px;
    border-radius: 8px;
    font-size: 0.78rem;
    margin-bottom: 4px;
}
.sidebar-status.loaded { background: rgba(16,185,129,0.15); color: #6EE7B7; }
.sidebar-status.empty  { background: rgba(100,116,139,0.15); color: #94A3B8; }
.dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.dot.green { background: #10B981; box-shadow: 0 0 6px #10B981; }
.dot.gray  { background: #475569; }

/* ── Divider ── */
.styled-divider {
    height: 1px;
    background: linear-gradient(to right, transparent, #E2E8F0 20%, #E2E8F0 80%, transparent);
    margin: 20px 0;
}
</style>
""", unsafe_allow_html=True)


# ── Helper functions ───────────────────────────────────────────────────────

def kpi_card(icon, value, label, colour="blue"):
    return f"""
    <div class="kpi-card {colour}">
        <span class="kpi-icon">{icon}</span>
        <div class="kpi-value">{value}</div>
        <div class="kpi-label">{label}</div>
    </div>"""

def section_header(title, icon=""):
    st.markdown(f"""
    <div class="section-header">
        <h3>{icon} {title}</h3>
        <div class="section-line"></div>
    </div>""", unsafe_allow_html=True)

def badge(text, level="ok"):
    colours = {"High":"high","Medium":"medium","Low":"low","ok":"ok","exact":"ok","fuzzy":"medium","unmatched":"high"}
    cls = colours.get(text, colours.get(level, "ok"))
    dots = {"high":"🔴","medium":"🟡","low":"🟢","ok":"🔵"}
    return f'<span class="badge badge-{cls}">{dots.get(cls,"")} {text}</span>'

def plotly_theme():
    """Shared base layout. No axis/margin keys — set those per chart to avoid duplicate kwarg errors."""
    return dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", size=11, color="#334155"),
        colorway=["#3B82F6","#10B981","#F59E0B","#EF4444","#8B5CF6","#06B6D4"],
    )

M = dict(l=16, r=16, t=24, b=16)   # default margin — override per chart

AX = dict(gridcolor="#F1F5F9", linecolor="#E2E8F0", zerolinecolor="#E2E8F0")


# ═══════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("""
    <div style="padding: 8px 0 20px;">
        <div style="font-size:1.1rem;font-weight:700;color:#F1F5F9;letter-spacing:-0.02em;">
            📊 Reg Reviewer
        </div>
        <div style="font-size:0.7rem;color:#475569;margin-top:2px;text-transform:uppercase;letter-spacing:0.1em;">
            HKIA FCA · AI-powered
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div style="font-size:0.72rem;color:#64748B;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:8px;">Upload Files</div>', unsafe_allow_html=True)

    cy_file = st.file_uploader("Current Year (CY)", type=["xlsx"], key="cy")
    st.markdown(
        f'<div class="sidebar-status {"loaded" if cy_file else "empty"}">'
        f'<div class="dot {"green" if cy_file else "gray"}"></div>'
        f'{"CY: " + cy_file.name[:22] if cy_file else "No CY file"}'
        f'</div>', unsafe_allow_html=True)

    py_file = st.file_uploader("Prior Year (PY)", type=["xlsx"], key="py")
    st.markdown(
        f'<div class="sidebar-status {"loaded" if py_file else "empty"}">'
        f'<div class="dot {"green" if py_file else "gray"}"></div>'
        f'{"PY: " + py_file.name[:22] if py_file else "No PY file"}'
        f'</div>', unsafe_allow_html=True)

    st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)

    run_disabled = not (cy_file and py_file)
    if st.button("▶  Run Analysis", type="primary", disabled=run_disabled, use_container_width=True):
        with st.spinner("Running full analysis…"):
            files = {
                "cy_file": ("cy.xlsx", cy_file.getvalue(),
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
                "py_file": ("py.xlsx", py_file.getvalue(),
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
            }
            try:
                resp = httpx.post(f"{BACKEND_URL}/compare", files=files, timeout=600)
                resp.raise_for_status()
                st.session_state["results"] = resp.json()
                for k in ["xlsx_bytes","memo","pdf_bytes","export_mode","gen_pdf","wf_findings"]:
                    st.session_state.pop(k, None)
            except httpx.ConnectError:
                st.error("Backend offline.")
            except Exception as e:
                st.error(str(e))

    # Status indicator
    if "results" in st.session_state:
        data = st.session_state["results"]
        all_df_sb = pd.DataFrame([
            dict(row, tab=tr["tab"])
            for tr in data["results"] for row in tr["data"]
        ])
        hi = int((all_df_sb.get("priority","") == "High").sum()) if "priority" in all_df_sb.columns else 0
        st.markdown(f"""
        <div style="margin-top:16px;padding:12px;background:rgba(16,185,129,0.1);
                    border:1px solid rgba(16,185,129,0.2);border-radius:10px;">
            <div style="font-size:0.7rem;color:#6EE7B7;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:6px;">
                ✅ Analysis Ready
            </div>
            <div style="font-size:0.82rem;color:#A7F3D0;">
                {len(data["results"])} tabs &nbsp;·&nbsp; {hi} high-priority
            </div>
        </div>""", unsafe_allow_html=True)

    st.markdown('<div style="height:24px;"></div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size:0.68rem;color:#334155;text-align:center;line-height:1.5;">'
                'Smart Regulatory Reviewer<br>AI-assisted · Not for submission</div>',
                unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# MAIN AREA
# ═══════════════════════════════════════════════════════════════════════════

# Page header
st.markdown("""
<div class="page-header">
    <div class="header-badge">HKIA FCA · YE2025 vs YE2024</div>
    <h1>Smart Regulatory Reviewer</h1>
    <p>AI-powered year-on-year comparison, exception detection, and actuarial commentary</p>
</div>
""", unsafe_allow_html=True)

if "results" not in st.session_state:
    st.markdown("""
    <div style="text-align:center;padding:80px 40px;color:#64748B;">
        <div style="font-size:3rem;margin-bottom:16px;">⬆</div>
        <div style="font-size:1rem;font-weight:600;color:#374151;margin-bottom:8px;">
            Upload files to begin
        </div>
        <div style="font-size:0.85rem;line-height:1.6;max-width:400px;margin:0 auto;">
            Upload your CY and PY Excel files in the sidebar,
            then click <strong>Run Analysis</strong>.
        </div>
    </div>""", unsafe_allow_html=True)
    st.stop()

data   = st.session_state["results"]
hkrbc  = data.get("hkrbc", {}) or {}
cy_cap = hkrbc.get("cy", {}) or {}
py_cap = hkrbc.get("py", {}) or {}

# Flat movements DF
rows_flat = []
for tr in data["results"]:
    for row in tr["data"]:
        row = dict(row); row["tab"] = tr["tab"]; rows_flat.append(row)
all_df = pd.DataFrame(rows_flat)
for col in ["cy_value","py_value","abs_movement","pct_change","materiality_pct","z_score"]:
    if col in all_df.columns:
        all_df[col] = pd.to_numeric(all_df[col], errors="coerce")

def _v(d, k):
    try: return float(d.get(k) or 0) or None
    except: return None

TABS = st.tabs(["🏠 Dashboard","📈 Movements","🔗 Alignment",
                "✅ CCR Checks","🤖 AI Notes","📄 Exec Summary","⬇ Export"])


# ═══════════════════════════════════════════════════════════════════════════
# TAB 0 — DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════
with TABS[0]:

    high_count   = int((all_df["priority"]=="High").sum()) if "priority" in all_df.columns else 0
    medium_count = int((all_df["priority"]=="Medium").sum()) if "priority" in all_df.columns else 0
    missing_tabs = sum(1 for f in data.get("ccr_findings",[])
                       if f.get("check")=="Completeness" and "missing" in f.get("finding","").lower())
    emerged      = sum(1 for f in data.get("ccr_findings",[])
                       if any(k in f.get("finding","") for k in ["EMERGED","DISAPPEARED"]))
    pca_ratio    = _v(cy_cap, "pca_ratio")
    pca_str      = f"{pca_ratio:.0f}%" if pca_ratio else "N/A"

    st.markdown(f"""
    <div class="kpi-grid">
        {kpi_card("📋", len(data["results"]), "Tabs Reviewed", "blue")}
        {kpi_card("🔴", high_count, "High Priority", "red")}
        {kpi_card("🟡", medium_count, "Medium Priority", "amber")}
        {kpi_card("⚠️", missing_tabs, "Missing Tabs", "orange")}
        {kpi_card("🔍", emerged, "Zero Emergence", "violet")}
        {kpi_card("🏛", pca_str, "PCA Coverage", "slate")}
    </div>
    """, unsafe_allow_html=True)

    # Row A: Top movers + BS comparison
    col_l, col_r = st.columns([3, 2], gap="medium")

    with col_l:
        section_header("Top 15 Movements", "🏆")
        top = (all_df.dropna(subset=["pct_change"])
               .assign(abs_pct=all_df["pct_change"].abs())
               .nlargest(15, "abs_pct")).copy()
        if not top.empty:
            top["label"]  = top["description"].str[:40] + "  (" + top["tab"].str[:10] + ")"
            pri_map = {"High":"#EF4444","Medium":"#F59E0B","Low":"#10B981"}
            top["colour"] = top["priority"].map(pri_map).fillna("#94A3B8")
            fig = go.Figure(go.Bar(
                x=top["pct_change"], y=top["label"], orientation="h",
                marker=dict(color=top["colour"], line=dict(width=0)),
                text=top["pct_change"].map(lambda v: f"{v:+.1f}%"),
                textposition="outside",
                hovertemplate="<b>%{y}</b><br>%{x:+.1f}%<extra></extra>",
            ))
            fig.update_layout(**plotly_theme(), height=420, margin=dict(l=16,r=80,t=24,b=16),
                yaxis=dict(autorange="reversed", **AX),
                xaxis=dict(title="% Change YoY", **AX))
            st.plotly_chart(fig, use_container_width=True)

    with col_r:
        section_header("Balance Sheet (HKD '000)", "🏦")
        bs_labels = ["Total Assets","Total Liabilities","Ins. Liabilities","MOCE","Eligible Cap.","PCA","MCA"]
        bs_keys   = ["total_assets","total_liabilities","insurance_liabilities","moce","eligible_capital","pca","mca"]
        cy_vals = [_v(cy_cap, k) for k in bs_keys]
        py_vals = [_v(py_cap, k) for k in bs_keys]
        if any(cy_vals):
            fig_bs = go.Figure()
            fig_bs.add_trace(go.Bar(name="YE25", y=bs_labels, x=cy_vals, orientation="h",
                marker=dict(color="#3B82F6", line=dict(width=0)),
                hovertemplate="<b>%{y}</b><br>YE25: %{x:,.0f}<extra></extra>"))
            fig_bs.add_trace(go.Bar(name="YE24", y=bs_labels, x=py_vals, orientation="h",
                marker=dict(color="#BFDBFE", line=dict(width=0)),
                hovertemplate="<b>%{y}</b><br>YE24: %{x:,.0f}<extra></extra>"))
            fig_bs.update_layout(**plotly_theme(), barmode="group", height=420, margin=dict(l=16,r=16,t=40,b=16),
                xaxis=dict(tickformat=",.0f", **AX),
                yaxis=AX,
                legend=dict(orientation="h", y=1.05, x=0))
            st.plotly_chart(fig_bs, use_container_width=True)

    st.markdown('<div class="styled-divider"></div>', unsafe_allow_html=True)

    # Row B: Waterfall
    section_header("Asset Movement Bridge — PY to CY", "🌉")
    f1_data = next((tr for tr in data["results"]
                    if "F.1" in tr["tab"] and "EBS" in tr["tab"] and "F.1B" not in tr["tab"]), None)
    if f1_data:
        wf_df = pd.DataFrame(f1_data["data"])
        for c in ["abs_movement","cy_value","py_value"]:
            wf_df[c] = pd.to_numeric(wf_df[c], errors="coerce")
        excl = ["summation","total assets","total liabilities","total equity","net assets","shareholders"]
        mask = ~wf_df["description"].str.lower().str.contains("|".join(excl), na=False)
        detail = wf_df[mask].dropna(subset=["abs_movement","py_value","cy_value"])
        detail = detail[detail["abs_movement"].abs() > 0]
        pos = detail[detail["abs_movement"]>0].nlargest(8, "abs_movement")
        neg = detail[detail["abs_movement"]<0].nsmallest(4, "abs_movement")
        drivers = pd.concat([pos,neg]).sort_values("abs_movement", ascending=False)
        if not drivers.empty:
            py_tot = float(_v(py_cap,"total_assets") or detail["py_value"].sum())
            cy_tot = float(_v(cy_cap,"total_assets") or detail["cy_value"].sum())
            other  = (cy_tot - py_tot) - drivers["abs_movement"].sum()
            labels   = (["YE24 Total Assets"] + drivers["description"].str[:32].tolist()
                        + (["Other movements"] if abs(other)>1000 else []) + ["YE25 Total Assets"])
            values   = ([py_tot] + drivers["abs_movement"].tolist()
                        + ([other] if abs(other)>1000 else []) + [cy_tot])
            measures = (["absolute"] + ["relative"]*len(drivers)
                        + (["relative"] if abs(other)>1000 else []) + ["total"])
            fig_wf = go.Figure(go.Waterfall(
                orientation="v", measure=measures, x=labels, y=values,
                connector=dict(line=dict(color="#E2E8F0", width=1, dash="dot")),
                increasing=dict(marker=dict(color="#10B981", line=dict(width=0))),
                decreasing=dict(marker=dict(color="#EF4444", line=dict(width=0))),
                totals=dict(marker=dict(color="#3B82F6", line=dict(width=0))),
                text=[f"{v:,.0f}" for v in values],
                textposition="outside",
                hovertemplate="<b>%{x}</b><br>%{y:,.0f}<extra></extra>",
            ))
            fig_wf.update_layout(**plotly_theme(), height=420,
                yaxis=dict(tickformat=",.0f", title="HKD Thousands", **AX),
                xaxis=dict(tickangle=-30, **AX),
                showlegend=False,
                margin=dict(l=16,r=16,t=24,b=130))
            st.plotly_chart(fig_wf, use_container_width=True)

    st.markdown('<div class="styled-divider"></div>', unsafe_allow_html=True)

    # Row C: HKRBC
    section_header("HKRBC Capital Structure", "🏛")

    def _segs(d):
        ta=_v(d,"total_assets") or 0; tl=_v(d,"total_liabilities") or 0
        il=_v(d,"insurance_liabilities") or 0; moce=_v(d,"moce") or 0
        pca=_v(d,"pca") or 0; mca=_v(d,"mca") or 0
        ol=max(0,tl-il); ce=max(0,il-moce); cap=max(0,ta-tl)
        mz=min(mca,cap); pb=min(max(0,pca-mca),max(0,cap-mz)); ex=max(0,cap-mz-pb)
        return dict(ta=ta,tl=tl,ol=ol,ce=ce,moce=moce,mz=mz,pb=pb,ex=ex,
                    pca=pca,mca=mca,pca_ratio=_v(d,"pca_ratio"),mca_ratio=_v(d,"mca_ratio"))

    cy_seg = _segs(cy_cap); py_seg = _segs(py_cap)

    if cy_seg["ta"] > 0 or py_seg["ta"] > 0:
        SEGS=[("Other Liabilities","ol","#475569"),("Current Estimate (CE)","ce","#60A5FA"),
              ("MOCE","moce","#FBBF24"),("MCA Zone","mz","#F87171"),
              ("PCA Buffer","pb","#FB923C"),("Excess Capital","ex","#34D399")]
        fig_h = go.Figure()
        fig_h.add_trace(go.Bar(name="Total Assets",
            x=["YE25 — Assets","YE24 — Assets"],
            y=[cy_seg["ta"],py_seg["ta"]],
            marker=dict(color="#CBD5E1", line=dict(width=0)), showlegend=True))
        for sn,sk,sc in SEGS:
            fig_h.add_trace(go.Bar(name=sn,
                x=["YE25 — Capital","YE24 — Capital"],
                y=[cy_seg[sk],py_seg[sk]],
                marker=dict(color=sc, line=dict(width=0)), showlegend=True))
        fig_h.update_layout(**plotly_theme(), barmode="stack", height=480,
            yaxis=dict(tickformat=",.0f", title="HKD Thousands", **AX),
            xaxis=AX,
            legend=dict(orientation="h", y=-0.18, x=0.5, xanchor="center"),
            margin=dict(l=16,r=16,t=24,b=20))
        for seg, xi, lbl in [(cy_seg,2,"YE25"),(py_seg,3,"YE24")]:
            if not seg["pca"]: continue
            for y_val, tag, colour, dash in [
                (seg["tl"]+seg["mca"],"MCA","#F97316","dot"),
                (seg["tl"]+seg["pca"],"PCA","#DC2626","dash"),
            ]:
                val = seg["mca"] if tag=="MCA" else seg["pca"]
                fig_h.add_shape(type="line",x0=xi-0.38,x1=xi+0.38,y0=y_val,y1=y_val,
                    xref="x",yref="y",line=dict(color=colour,width=2.5,dash=dash))
                fig_h.add_annotation(x=xi+0.36,y=y_val,
                    text=f"<b>{tag} {lbl}: {val:,.0f}</b>",
                    showarrow=False,xanchor="right",yanchor="bottom",
                    font=dict(color=colour,size=10),
                    bgcolor="rgba(255,255,255,0.9)",bordercolor=colour,borderwidth=1,
                    xref="x",yref="y")
        st.plotly_chart(fig_h, use_container_width=True)

        # Ratio cards
        r1,r2,r3,r4 = st.columns(4, gap="small")
        def _rm(col, lbl, v, py_v, thr):
            if v and v>0:
                ok = v >= thr
                icon = "🟢" if ok else "🔴"
                col.markdown(f"""
                <div class="kpi-card {"blue" if ok else "red"}" style="text-align:center">
                    <div style="font-size:1.4rem">{icon}</div>
                    <div class="kpi-value">{v:.1f}%</div>
                    <div class="kpi-label">{lbl}</div>
                    {'<div style="font-size:0.7rem;color:#10B981;margin-top:4px;">▲ ' + f'{v-py_v:+.1f}pp vs PY</div>' if py_v and py_v>0 else ''}
                </div>""", unsafe_allow_html=True)
            else:
                col.markdown(f'<div class="kpi-card slate" style="text-align:center"><div class="kpi-value">N/A</div><div class="kpi-label">{lbl}</div></div>', unsafe_allow_html=True)
        _rm(r1,"PCA Coverage CY",cy_seg["pca_ratio"],py_seg["pca_ratio"],150)
        _rm(r2,"MCA Coverage CY",cy_seg["mca_ratio"],py_seg["mca_ratio"],200)
        _rm(r3,"PCA Coverage PY",py_seg["pca_ratio"],None,150)
        _rm(r4,"MCA Coverage PY",py_seg["mca_ratio"],None,200)

        cap_comment = hkrbc.get("ai_commentary","")
        if cap_comment and not cap_comment.startswith("["):
            st.markdown('<div style="height:12px;"></div>', unsafe_allow_html=True)
            section_header("AI Capital Commentary", "🤖")
            st.markdown(f'<div class="comment-bubble" style="padding-top:24px;">{cap_comment}</div>',
                        unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# TAB 1 — MOVEMENTS
# ═══════════════════════════════════════════════════════════════════════════
RENAME = {"description":"Description","cy_code":"Code",
          "cy_value":"CY Value","py_value":"PY Value",
          "abs_movement":"Movement","pct_change":"Change %",
          "materiality_pct":"Materiality %","priority":"Priority","match_status":"Match"}
NUM_FORMAT = {"CY Value":"{:,.0f}","PY Value":"{:,.0f}","Movement":"{:,.0f}",
              "Change %":"{:.1f}%","Materiality %":"{:.1f}%"}

with TABS[1]:
    section_header("Year-on-Year Movements by Tab", "📈")

    # Summary row
    if not all_df.empty and "priority" in all_df.columns:
        hi = (all_df["priority"]=="High").sum()
        med = (all_df["priority"]=="Medium").sum()
        lo = (all_df["priority"]=="Low").sum()
        st.markdown(f"""
        <div style="display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap;">
            <span class="badge badge-high">🔴 {hi} High</span>
            <span class="badge badge-medium">🟡 {med} Medium</span>
            <span class="badge badge-low">🟢 {lo} Low</span>
        </div>""", unsafe_allow_html=True)

    def _pc(v):
        c={"High":"#FEE2E2","Medium":"#FEF3C7","Low":"#D1FAE5"}
        return f"background-color:{c[v]};font-weight:500" if v in c else ""

    for tr in data["results"]:
        df_r = pd.DataFrame(tr["data"])
        if df_r.empty: continue
        avail = [c for c in RENAME if c in df_r.columns]
        df_s  = df_r[avail].rename(columns=RENAME)
        hi    = int((df_s["Priority"]=="High").sum()) if "Priority" in df_s.columns else 0
        med   = int((df_s["Priority"]=="Medium").sum()) if "Priority" in df_s.columns else 0
        lbl   = f"📋 {tr['tab']}  ·  {len(df_s)} rows"
        if hi:  lbl += f"  ·  🔴 {hi} High"
        if med: lbl += f"  ·  🟡 {med} Medium"
        with st.expander(lbl, expanded=(hi > 0)):
            fmt = {k:v for k,v in NUM_FORMAT.items() if k in df_s.columns}
            st.dataframe(
                df_s.style.map(_pc, subset=["Priority"]).format(fmt, na_rep="—"),
                use_container_width=True, height=min(400, 50+len(df_s)*35))


# ═══════════════════════════════════════════════════════════════════════════
# TAB 2 — TAB ALIGNMENT
# ═══════════════════════════════════════════════════════════════════════════
with TABS[2]:
    section_header("Tab Matching: CY → PY", "🔗")
    rows = [{"CY Tab":cy,"PY Tab":i["py_tab"],"Score":i["score"],"Status":i["status"]}
            for cy,i in data["tab_alignment"].items()]
    adf = pd.DataFrame(rows)
    total = len(adf)
    exact = (adf["Status"]=="exact").sum()
    fuzzy = (adf["Status"]=="fuzzy").sum()
    unmat = (adf["Status"]=="unmatched").sum()

    m1,m2,m3,m4 = st.columns(4)
    m1.markdown(f'<div class="kpi-card blue"><span class="kpi-icon">📂</span><div class="kpi-value">{total}</div><div class="kpi-label">Total Tabs</div></div>', unsafe_allow_html=True)
    m2.markdown(f'<div class="kpi-card slate"><span class="kpi-icon">✅</span><div class="kpi-value">{exact}</div><div class="kpi-label">Exact Match</div></div>', unsafe_allow_html=True)
    m3.markdown(f'<div class="kpi-card amber"><span class="kpi-icon">🔀</span><div class="kpi-value">{fuzzy}</div><div class="kpi-label">Fuzzy Match</div></div>', unsafe_allow_html=True)
    m4.markdown(f'<div class="kpi-card red"><span class="kpi-icon">❌</span><div class="kpi-value">{unmat}</div><div class="kpi-label">Unmatched</div></div>', unsafe_allow_html=True)

    st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)

    def _sc(v):
        c={"exact":"#D1FAE5","fuzzy":"#FEF3C7","unmatched":"#FEE2E2"}
        return f"background-color:{c[v]}" if v in c else ""
    st.dataframe(adf.style.map(_sc,subset=["Status"]).format({"Score":"{:.0f}"}),
                 use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════
# TAB 3 — CCR CHECKS
# ═══════════════════════════════════════════════════════════════════════════
with TABS[3]:
    section_header("Completeness · Consistency · Reasonableness", "✅")
    ccr_df = pd.DataFrame(data.get("ccr_findings",[]))

    if not ccr_df.empty:
        total_ccr = len(ccr_df)
        hi_ccr    = int((ccr_df["severity"]=="High").sum())
        med_ccr   = int((ccr_df["severity"]=="Medium").sum())
        st.markdown(f"""
        <div style="display:flex;gap:8px;margin-bottom:16px;">
            <span class="badge badge-high">🔴 {hi_ccr} High</span>
            <span class="badge badge-medium">🟡 {med_ccr} Medium</span>
            <span class="badge badge-ok">📋 {total_ccr} Total</span>
        </div>""", unsafe_allow_html=True)

    ccr_sub = st.tabs(["🔍 Completeness","🔗 Consistency","📐 Reasonableness","📎 Working File"])

    def _sev_cls(sev): return "high" if sev=="High" else "medium" if sev=="Medium" else ""

    def render_ccr_cards(df_subset):
        if df_subset.empty:
            st.markdown('<div style="padding:20px;text-align:center;color:#10B981;font-size:0.85rem;">✅ No issues found</div>', unsafe_allow_html=True)
            return
        for _, row in df_subset.iterrows():
            sev = row.get("severity","")
            st.markdown(f"""
            <div class="ccr-card {_sev_cls(sev)}">
                <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;">
                    <div class="ccr-check-type">{row.get('check','')} · {row.get('tab','')}</div>
                    {badge(sev)}
                </div>
                <div class="ccr-finding">{row.get('finding','')}</div>
            </div>""", unsafe_allow_html=True)

    with ccr_sub[0]:
        comp = ccr_df[ccr_df["check"]=="Completeness"] if not ccr_df.empty else pd.DataFrame()
        if not comp.empty:
            for label, keyword in [("Missing Tabs","missing from"),
                                   ("Disappeared Items","DISAPPEARED"),
                                   ("Emerged Items","EMERGED")]:
                sub = comp[comp["finding"].str.contains(keyword, na=False)]
                if not sub.empty:
                    st.markdown(f'<div style="font-size:0.78rem;font-weight:600;color:#1E293B;text-transform:uppercase;letter-spacing:0.06em;margin:12px 0 6px;">{label} ({len(sub)})</div>', unsafe_allow_html=True)
                    render_ccr_cards(sub)
        else:
            render_ccr_cards(pd.DataFrame())

    with ccr_sub[1]:
        cons = ccr_df[ccr_df["check"]=="Consistency"] if not ccr_df.empty else pd.DataFrame()
        sub_totals = cons[~cons["finding"].str.contains("WORKING FILE", na=False)] if not cons.empty else pd.DataFrame()
        render_ccr_cards(sub_totals)

    with ccr_sub[2]:
        reason = ccr_df[ccr_df["check"]=="Reasonableness"] if not ccr_df.empty else pd.DataFrame()
        if not reason.empty:
            tab_counts = reason.groupby(["tab","severity"]).size().unstack(fill_value=0).reset_index()
            for col in ["High","Medium"]:
                if col not in tab_counts.columns: tab_counts[col] = 0
            tab_counts = tab_counts.sort_values("High", ascending=False).head(10)
            fig_r = go.Figure()
            for sev, colour in [("High","#EF4444"),("Medium","#F59E0B")]:
                fig_r.add_trace(go.Bar(name=sev, x=tab_counts["tab"], y=tab_counts[sev],
                    marker=dict(color=colour, line=dict(width=0))))
            fig_r.update_layout(**plotly_theme(), barmode="stack", height=260,
                xaxis=dict(tickangle=-30, **AX),
                yaxis=dict(title="Findings", **AX),
                margin=dict(l=16,r=16,t=16,b=80))
            st.plotly_chart(fig_r, use_container_width=True)
            render_ccr_cards(reason)
        else:
            render_ccr_cards(pd.DataFrame())

    with ccr_sub[3]:
        st.markdown("""
        <div style="background:#F0F9FF;border:1px solid #BAE6FD;border-radius:10px;
                    padding:16px;margin-bottom:16px;font-size:0.83rem;color:#0C4A6E;line-height:1.6;">
            Upload underlying working papers. The system fuzzy-matches account labels
            and flags values that differ from the FCA return beyond your chosen tolerance.
        </div>""", unsafe_allow_html=True)

        wf_upload = st.file_uploader("Working paper Excel file", type=["xlsx"], key="working_file")
        tolerance = st.slider("Tolerance (%)", 0.5, 10.0, 1.0, 0.5)

        if wf_upload and cy_file:
            if st.button("🔍 Run Cross-Check", type="primary"):
                with st.spinner("Cross-checking…"):
                    files = {
                        "cy_file": ("cy.xlsx", cy_file.getvalue(),
                                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
                        "working_file": ("working.xlsx", wf_upload.getvalue(),
                                         "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
                    }
                    try:
                        resp = httpx.post(f"{BACKEND_URL}/check_working_file",
                                          files=files, timeout=120)
                        resp.raise_for_status()
                        st.session_state["wf_findings"] = resp.json().get("findings",[])
                    except Exception as e:
                        st.error(str(e))

        if st.session_state.get("wf_findings") is not None:
            wf = st.session_state["wf_findings"]
            if wf:
                render_ccr_cards(pd.DataFrame(wf))
            else:
                st.success("✅ No discrepancies found.")
        elif not wf_upload:
            st.info("Upload a working file above to start the cross-check.")


# ═══════════════════════════════════════════════════════════════════════════
# TAB 4 — AI COMMENTARY
# ═══════════════════════════════════════════════════════════════════════════
with TABS[4]:
    section_header("Auto-drafted Reviewer Notes", "🤖")
    st.markdown('<div style="font-size:0.8rem;color:#64748B;margin-bottom:16px;">AI-generated exception notes for High-priority items. Validate before use.</div>', unsafe_allow_html=True)

    commentary = data.get("commentary",[])
    if commentary:
        for item in commentary:
            pct  = item.get("pct_change")
            cy_v = float(item.get("cy_value") or 0)
            py_v = float(item.get("py_value") or 0)
            pct_str = f"{pct:+.1f}%" if pct is not None else "N/A"
            colour = "#EF4444" if (pct or 0) > 0 else "#10B981"

            st.markdown(f"""
            <div style="background:white;border:1px solid #E2E8F0;border-radius:14px;
                        padding:20px;margin-bottom:16px;animation:fadeInUp 0.3s ease both;">
                <div class="comment-header">
                    <div class="comment-title">{item.get('description','Unknown')}</div>
                    <div style="display:flex;gap:6px;align-items:center;">
                        <span style="font-size:0.75rem;color:#64748B;">{item.get('tab','')}</span>
                        {badge(item.get('priority','Low'))}
                    </div>
                </div>
                <div class="comment-metrics">
                    <div class="comment-metric">
                        <div class="comment-metric-val">{cy_v:,.0f}</div>
                        <div class="comment-metric-lbl">CY Value</div>
                    </div>
                    <div class="comment-metric">
                        <div class="comment-metric-val">{py_v:,.0f}</div>
                        <div class="comment-metric-lbl">PY Value</div>
                    </div>
                    <div class="comment-metric">
                        <div class="comment-metric-val" style="color:{colour};">{pct_str}</div>
                        <div class="comment-metric-lbl">YoY Change</div>
                    </div>
                </div>
                <div class="comment-bubble" style="padding-top:22px;margin:0;">
                    {item.get('commentary','No commentary generated.')}
                </div>
            </div>""", unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="text-align:center;padding:60px;color:#94A3B8;">
            <div style="font-size:2rem;margin-bottom:12px;">🤖</div>
            No high-priority commentary generated.
        </div>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# TAB 5 — EXECUTIVE SUMMARY
# ═══════════════════════════════════════════════════════════════════════════
with TABS[5]:
    section_header("AI Executive Summary Memo", "📄")
    st.markdown('<div style="font-size:0.8rem;color:#64748B;margin-bottom:16px;">One-click actuarial review memo: capital position · material movements · CCR findings · recommended actions.</div>', unsafe_allow_html=True)

    if st.button("🤖 Generate Executive Summary", type="primary", use_container_width=True):
        st.session_state["memo"] = None
        with st.spinner("Kimi-K2.5 is drafting the memo…"):
            try:
                resp = httpx.post(f"{BACKEND_URL}/executive_summary",
                    json={"hkrbc": data.get("hkrbc",{}),
                          "results": data["results"],
                          "ccr_findings": data.get("ccr_findings",[])},
                    timeout=300)
                resp.raise_for_status()
                st.session_state["memo"] = resp.json()
            except Exception as e:
                st.error(str(e))

    memo = st.session_state.get("memo")
    if memo:
        cap = memo.get("capital",{})
        top = memo.get("top_movements",[])
        sections = memo.get("sections",{})
        has_sections = any(v.strip() for v in sections.values())

        st.markdown(f"""
        <div class="memo-container">
            <div class="memo-title">ACTUARIAL REVIEW MEMO — HKIA FCA REGULATORY RETURN</div>
            <div class="memo-meta">
                YE2025 vs YE2024 &nbsp;·&nbsp; Prepared: {memo.get('memo_date','')} &nbsp;·&nbsp;
                <strong>CONFIDENTIAL</strong> &nbsp;·&nbsp; AI-Assisted Draft
            </div>
        """, unsafe_allow_html=True)

        # Capital strip
        pc = _v(cap,"pca_ratio"); mc = _v(cap,"mca_ratio")
        st.markdown(f"""
            <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20px;">
                <div style="text-align:center;padding:12px;background:#F8FAFC;border-radius:8px;">
                    <div style="font-size:1.1rem;font-weight:700;color:#0F172A;">{f'{float(cap.get("eligible_capital") or 0):,.0f}' if cap.get("eligible_capital") else "N/A"}</div>
                    <div style="font-size:0.68rem;color:#64748B;text-transform:uppercase;letter-spacing:0.06em;">Eligible Capital</div>
                </div>
                <div style="text-align:center;padding:12px;background:#F0FDF4;border-radius:8px;border:1px solid #BBF7D0;">
                    <div style="font-size:1.1rem;font-weight:700;color:#065F46;">{f"{pc:.1f}%" if pc else "N/A"}</div>
                    <div style="font-size:0.68rem;color:#064E3B;text-transform:uppercase;letter-spacing:0.06em;">PCA Coverage</div>
                </div>
                <div style="text-align:center;padding:12px;background:#EFF6FF;border-radius:8px;border:1px solid #BFDBFE;">
                    <div style="font-size:1.1rem;font-weight:700;color:#1E40AF;">{f"{mc:.1f}%" if mc else "N/A"}</div>
                    <div style="font-size:0.68rem;color:#1E3A8A;text-transform:uppercase;letter-spacing:0.06em;">MCA Coverage</div>
                </div>
                <div style="text-align:center;padding:12px;background:#F8FAFC;border-radius:8px;">
                    <div style="font-size:1.1rem;font-weight:700;color:#0F172A;">{f'{float(cap.get("total_assets") or 0):,.0f}' if cap.get("total_assets") else "N/A"}</div>
                    <div style="font-size:0.68rem;color:#64748B;text-transform:uppercase;letter-spacing:0.06em;">Total Assets</div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        section_names = {
            "SECTION 1":"1. CAPITAL ADEQUACY OVERVIEW",
            "SECTION 2":"2. MATERIAL MOVEMENTS COMMENTARY",
            "SECTION 3":"3. CCR FINDINGS SUMMARY",
            "SECTION 4":"4. RECOMMENDED FOLLOW-UP ACTIONS",
        }
        if has_sections:
            for key, title in section_names.items():
                text = sections.get(key,"").strip()
                if text:
                    st.markdown(f'<div class="memo-section-title">{title}</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="memo-text">{text}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="memo-text">{memo.get("ai_narrative","")}</div>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

        # PDF button
        st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)
        if st.button("📄 Download as PDF", use_container_width=True):
            st.session_state["gen_pdf"] = True

        if st.session_state.get("gen_pdf"):
            with st.spinner("Building PDF…"):
                try:
                    resp = httpx.post(f"{BACKEND_URL}/executive_summary_pdf",
                        json={"hkrbc": data.get("hkrbc",{}),
                              "results": data["results"],
                              "ccr_findings": data.get("ccr_findings",[])},
                        timeout=300)
                    resp.raise_for_status()
                    st.session_state["pdf_bytes"] = resp.content
                    st.session_state["gen_pdf"] = False
                except Exception as e:
                    st.error(str(e)); st.session_state["gen_pdf"] = False

        if st.session_state.get("pdf_bytes"):
            st.download_button("📥 Save FCA_Review_Memo.pdf",
                data=st.session_state["pdf_bytes"],
                file_name="FCA_Review_Memo.pdf", mime="application/pdf",
                use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════
# TAB 6 — EXPORT
# ═══════════════════════════════════════════════════════════════════════════
with TABS[6]:
    section_header("Download Reports", "⬇")

    col_a, col_b, col_c = st.columns(3, gap="medium")

    with col_a:
        st.markdown("""
        <div class="export-card">
            <span class="export-icon">📊</span>
            <div class="export-title">Excel Report (with AI)</div>
            <div class="export-desc">Full FCA return with AI-generated remarks for all significant movements. Takes 3–8 min.</div>
        </div>""", unsafe_allow_html=True)
        st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)
        if st.button("🤖 Export with AI Remarks", type="primary", use_container_width=True):
            st.session_state["export_mode"] = "ai"

    with col_b:
        st.markdown("""
        <div class="export-card">
            <span class="export-icon">⚡</span>
            <div class="export-title">Excel Report (instant)</div>
            <div class="export-desc">Full FCA return with all movements. Remarks column blank. Ready in seconds.</div>
        </div>""", unsafe_allow_html=True)
        st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)
        if st.button("⚡ Export without AI Remarks", use_container_width=True):
            st.session_state["export_mode"] = "fast"

    with col_c:
        st.markdown("""
        <div class="export-card">
            <span class="export-icon">🗂</span>
            <div class="export-title">Raw JSON</div>
            <div class="export-desc">Complete analysis results in JSON format for downstream processing or archiving.</div>
        </div>""", unsafe_allow_html=True)
        st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)
        st.download_button("⬇ Download JSON",
            data=json.dumps(data, indent=2, default=str).encode(),
            file_name="fca_results.json", mime="application/json",
            use_container_width=True)

    st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)

    if st.session_state.get("export_mode"):
        ai = st.session_state["export_mode"] == "ai"
        with st.spinner("Generating Excel with AI remarks…" if ai else "Building Excel…"):
            try:
                resp = httpx.post(f"{BACKEND_URL}/export_results",
                    json={"results": data["results"], "ai_remarks": ai}, timeout=600)
                resp.raise_for_status()
                st.session_state["xlsx_bytes"] = resp.content
                st.session_state["export_mode"] = None
            except Exception as e:
                st.error(str(e)); st.session_state["export_mode"] = None

    if st.session_state.get("xlsx_bytes"):
        st.success("✅ Excel report ready.")
        st.download_button("📥 Save FCA_Review_Report.xlsx",
            data=st.session_state["xlsx_bytes"],
            file_name="FCA_Review_Report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True)