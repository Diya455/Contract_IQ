import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import tempfile
import hashlib
import pandas as pd
from datetime import datetime, date, timedelta
from ingestion.ocr_loader import extract_text_from_pdf
from ingestion.pdf_loader import chunk_text_clause_section_with_metadata, load_model, embed_chunks, generate_answer
from extraction.structured_extractor import extract_structured_data
from vectordb.weaviate_client import insert_document, create_schema, query_similar_chunks
from database.contracts_db import (
    init_db, insert_contract, get_all_contracts,
    get_total_contract_value, get_contracts_by_status,
    get_top_parties, get_contracts_by_month,
    get_risk_distribution, get_service_type_distribution,
    get_expiring_contracts
)
from database.users_db import init_users_table, create_default_admin, get_all_users, update_user_role, deactivate_user, activate_user
from analytics.contract_analytics import (
    extract_contract_value, calculate_risk_score,
    calculate_renewal_probability, determine_contract_status,
    analyze_contract_text, get_risk_category, get_risk_color,
    format_currency, calculate_portfolio_health
)
from alerts.expiry_engine import check_expiry_alerts
from auth.authenticator import (
    init_session_state,
    is_authenticated,
    is_admin,
    logout,
    show_auth_page,
    get_current_user
)

# ─── Page Config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ContractIQ",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    font-size: 14px;
}
.stApp { background: #0f1117; color: #f0f2f6; }

[data-testid="stSidebar"] {
    background: #1a1d24 !important;
    border-right: 1px solid #2d3140;
}
[data-testid="stSidebar"] .stRadio label {
    color: #c0c4d0 !important;
    font-size: 0.92rem;
    font-weight: 500;
}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 { color: #f0f2f6 !important; }

h1, h2, h3 { font-weight: 700 !important; letter-spacing: -0.01em; }

[data-testid="stFileUploader"] {
    background: #1e212c;
    border: 1.5px dashed #353a50;
    border-radius: 10px;
    padding: 6px;
}

.metric-card {
    background: #1e212c;
    border: 1px solid #2d3140;
    border-radius: 12px;
    padding: 18px 20px;
    position: relative;
    overflow: hidden;
    margin-bottom: 4px;
}
.metric-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    border-radius: 12px 12px 0 0;
}
.metric-card.green::before  { background: #22c55e; }
.metric-card.amber::before  { background: #f59e0b; }
.metric-card.red::before    { background: #ef4444; }
.metric-card.blue::before   { background: #3b82f6; }
.metric-card.gray::before   { background: #6b7280; }

.metric-value {
    font-size: 2rem;
    font-weight: 700;
    color: #f0f2f6;
    line-height: 1;
    margin: 6px 0 4px 0;
}
.metric-label {
    font-size: 0.75rem;
    color: #7b8299;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}
.metric-sub { font-size: 0.8rem; color: #9ba3b8; margin-top: 4px; }
.metric-icon { font-size: 1.3rem; margin-bottom: 4px; }

.badge {
    display: inline-block;
    padding: 2px 9px;
    border-radius: 4px;
    font-size: 0.71rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}
.badge-green  { background: rgba(34,197,94,0.15);  color: #4ade80; }
.badge-amber  { background: rgba(245,158,11,0.15); color: #fbbf24; }
.badge-red    { background: rgba(239,68,68,0.15);  color: #f87171; }
.badge-blue   { background: rgba(59,130,246,0.15); color: #60a5fa; }
.badge-gray   { background: rgba(107,114,128,0.15);color: #9ca3af; }

.section-title {
    font-size: 1rem;
    font-weight: 700;
    color: #f0f2f6;
    margin-bottom: 14px;
    padding-bottom: 8px;
    border-bottom: 1px solid #2d3140;
    display: flex;
    align-items: center;
    gap: 8px;
}

.contract-row {
    background: #1e212c;
    border: 1px solid #2d3140;
    border-radius: 8px;
    padding: 12px 16px;
    margin-bottom: 6px;
    display: flex;
    align-items: center;
    gap: 14px;
}

.timeline-bar {
    height: 5px;
    border-radius: 3px;
    background: #2d3140;
    overflow: hidden;
    margin-top: 5px;
}
.timeline-fill { height: 100%; border-radius: 3px; }

.alert-item {
    background: #1e212c;
    border-left: 3px solid;
    border-radius: 0 8px 8px 0;
    padding: 11px 15px;
    margin-bottom: 6px;
}
.alert-item.red   { border-color: #ef4444; }
.alert-item.amber { border-color: #f59e0b; }
.alert-item.green { border-color: #22c55e; }

.divider {
    height: 1px;
    background: #2d3140;
    margin: 22px 0;
}

.chat-user {
    background: #1e3a5f;
    border-radius: 12px 12px 3px 12px;
    padding: 10px 14px;
    margin: 6px 0;
    max-width: 78%;
    margin-left: auto;
    color: #bfdbfe;
    font-size: 0.9rem;
    line-height: 1.5;
}
.chat-assistant {
    background: #1e212c;
    border: 1px solid #2d3140;
    border-radius: 12px 12px 12px 3px;
    padding: 10px 14px;
    margin: 6px 0;
    max-width: 85%;
    color: #e8eaf0;
    font-size: 0.9rem;
    line-height: 1.5;
}

.stButton > button {
    background: #2563eb;
    color: white;
    border: none;
    border-radius: 7px;
    font-weight: 600;
    font-size: 0.85rem;
    padding: 7px 18px;
}
.stButton > button:hover { background: #1d4ed8; }

div[data-testid="stDataFrame"] {
    border-radius: 10px;
    border: 1px solid #2d3140;
}

p, li, span { color: #d1d5db; }
</style>
""", unsafe_allow_html=True)

# ─── Init ─────────────────────────────────────────────────────────────────────
if "initialized" not in st.session_state:
    init_db()
    init_users_table()
    create_default_admin()
    create_schema()
    st.session_state.initialized = True

if "processed_hashes" not in st.session_state:
    st.session_state.processed_hashes = set()

if "messages" not in st.session_state:
    st.session_state.messages = []

# Initialize authentication
init_session_state()

# ─── Authentication Check ─────────────────────────────────────────────────────
if not is_authenticated():
    show_auth_page()
    st.stop()

# ─── Helpers ──────────────────────────────────────────────────────────────────
def lifecycle_stage(row):
    today = date.today()
    effective = row.get("effective_date")
    expiry = row.get("expiry_date")

    if not effective and not expiry:
        return "Unknown"

    try:
        eff_dt = datetime.fromisoformat(effective).date() if effective else None
        exp_dt = datetime.fromisoformat(expiry).date() if expiry else None
    except Exception:
        return "Unknown"

    if eff_dt and exp_dt:
        if today < eff_dt:
            return "Pending"
        elif eff_dt <= today <= exp_dt:
            return "Active"
        else:
            return "Expired"
    elif eff_dt and today >= eff_dt:
        return "Active"
    elif exp_dt and today > exp_dt:
        return "Expired"

    return "Active"


# ═════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown(f"""
    <div style='text-align: center; padding: 16px 0 10px 0;'>
        <div style='font-size: 1.8rem; font-weight: 700; color: #f0f2f6;'>📋 ContractIQ</div>
        <div style='font-size: 0.75rem; color: #7b8299; margin-top: 4px;'>
            Logged in as <strong style='color: #60a5fa;'>{st.session_state.username}</strong>
            <br>
            Role: <span class='badge badge-blue'>{st.session_state.role}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='margin: 10px 0;'></div>", unsafe_allow_html=True)

    # Navigation
    pages = ["📤 Upload Contracts", "📊 Dashboard", "📈 Analytics Dashboard"]
    if is_admin():
        pages.append("👥 User Management")

    page = st.radio("Navigation", pages, label_visibility="collapsed")

    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

    # Logout button
    if st.button("🚪 Logout", use_container_width=True):
        logout()
        st.rerun()


# ═════════════════════════════════════════════════════════════════════════════
# PAGE: UPLOAD
# ═════════════════════════════════════════════════════════════════════════════
if page == "📤 Upload Contracts":

    st.markdown("""
    <div style='padding: 8px 0 20px 0;'>
        <div style='font-size: 1.6rem; font-weight: 700; color: #f0f2f6;'>
            Upload Contracts
        </div>
        <div style='font-size: 0.88rem; color: #7b8299; margin-top: 3px;'>
            Upload PDF contracts to extract key data and enable semantic search
        </div>
    </div>
    """, unsafe_allow_html=True)

    uploaded_files = st.file_uploader(
        "Choose PDF files",
        type=["pdf"],
        accept_multiple_files=True,
        label_visibility="collapsed"
    )

    if uploaded_files:
        if st.button("🚀 Process Contracts", use_container_width=True):
            progress_bar = st.progress(0)
            status_text = st.empty()

            for idx, uploaded_file in enumerate(uploaded_files):
                file_hash = hashlib.sha256(uploaded_file.read()).hexdigest()
                uploaded_file.seek(0)

                if file_hash in st.session_state.processed_hashes:
                    st.warning(f"⚠️ {uploaded_file.name} already processed. Skipping...")
                    continue

                status_text.text(f"Processing {uploaded_file.name}...")

                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(uploaded_file.read())
                    tmp_path = tmp.name

                try:
                    # Extract text
                    raw_text = extract_text_from_pdf(tmp_path)

                    if not raw_text.strip():
                        st.error(f"❌ {uploaded_file.name}: No text extracted")
                        continue

                    # Extract structured data
                    extracted = extract_structured_data(raw_text)

                    # Store in database with user_id
                    contract_data = {
                        "file_hash": file_hash,
                        "file_name": uploaded_file.name,
                        "effective_date": extracted.get("effective_date"),
                        "expiry_date": extracted.get("expiry_date"),
                        "party_1_name": extracted.get("party_1_name"),
                        "party_2_name": extracted.get("party_2_name"),
                        "service_type": extracted.get("service_type"),
                        "payment_basis": extracted.get("payment_basis"),
                        "user_id": st.session_state.user_id
                    }
                    insert_contract(contract_data)

                    # Generate embeddings
                    model = load_model()
                    pages_data = [{"page_number": 1, "text": raw_text}]
                    chunks = chunk_text_clause_section_with_metadata(pages_data)

                    for chunk in chunks:
                        chunk_text = chunk["content"]
                        embedding = embed_chunks([chunk_text], model)[0]
                        insert_document(
                            chunk_text,
                            embedding,
                            {"page_number": chunk["page_number"], "section_title": chunk["section_title"]}
                        )

                    st.session_state.processed_hashes.add(file_hash)
                    st.success(f"✅ {uploaded_file.name} processed successfully")

                except Exception as e:
                    st.error(f"❌ {uploaded_file.name}: {str(e)}")

                progress_bar.progress((idx + 1) / len(uploaded_files))

            status_text.text("✅ All files processed!")
            st.balloons()


# ═════════════════════════════════════════════════════════════════════════════
# PAGE: DASHBOARD
# ═════════════════════════════════════════════════════════════════════════════
elif page == "📊 Dashboard":

    st.markdown("""
    <div style='padding: 8px 0 20px 0;'>
        <div style='font-size: 1.6rem; font-weight: 700; color: #f0f2f6;'>
            Contract Dashboard
        </div>
        <div style='font-size: 0.88rem; color: #7b8299; margin-top: 3px;'>
            Monitor contract lifecycle, expiry alerts, and key metrics
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Get contracts for current user
    df = get_all_contracts(user_id=st.session_state.user_id, role=st.session_state.role)

    if df.empty:
        st.markdown("""
        <div style='text-align:center; padding:60px; background:#161820; border:1px solid #1e2130;
                    border-radius:14px; color:#6b7280;'>
            <div style='font-size:3rem; margin-bottom:12px;'>📋</div>
            <div style='font-size:1.1rem; color:#9ba3b8; font-weight:600;'>No Contracts Yet</div>
            <div style='font-size:0.88rem; margin-top:8px;'>
                Upload your first contract to get started
            </div>
        </div>""", unsafe_allow_html=True)
        st.stop()

    total = len(df)
    df["lifecycle_stage"] = df.apply(lifecycle_stage, axis=1)

    # Top metrics
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.markdown(f"""
        <div class='metric-card blue'>
            <div class='metric-label'>Total Contracts</div>
            <div class='metric-value'>{total}</div>
            <div class='metric-sub'>In your library</div>
        </div>""", unsafe_allow_html=True)

    active_count = len(df[df["lifecycle_stage"] == "Active"])
    with c2:
        st.markdown(f"""
        <div class='metric-card green'>
            <div class='metric-label'>Active</div>
            <div class='metric-value'>{active_count}</div>
            <div class='metric-sub'>{round(active_count/total*100) if total else 0}% of total</div>
        </div>""", unsafe_allow_html=True)

    expired_count = len(df[df["lifecycle_stage"] == "Expired"])
    with c3:
        st.markdown(f"""
        <div class='metric-card red'>
            <div class='metric-label'>Expired</div>
            <div class='metric-value'>{expired_count}</div>
            <div class='metric-sub'>Needs renewal</div>
        </div>""", unsafe_allow_html=True)

    pending_count = len(df[df["lifecycle_stage"] == "Pending"])
    with c4:
        st.markdown(f"""
        <div class='metric-card gray'>
            <div class='metric-label'>Pending</div>
            <div class='metric-value'>{pending_count}</div>
            <div class='metric-sub'>Not yet effective</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

    # Expiry alerts section
    st.markdown("""
    <div class='section-title'>
        <span style='color: #9ba3b8;'>⚠️</span> Expiry Alerts
    </div>""", unsafe_allow_html=True)

    st.markdown("""
    <div style='background: #161820; border: 1px solid #1e2130; border-radius: 10px;
                padding: 12px 18px; margin-bottom: 18px; font-size: 0.8rem; color: #6b7280;'>
        <span style='color:#9ba3b8; font-weight:600;'>Alert Thresholds:</span>
        &nbsp; 🔴 Expired
        &nbsp;|&nbsp; 🟡 &lt;14 days (Small) / &lt;28 days (Mid) / &lt;60 days (Enterprise)
        &nbsp;|&nbsp; 🟢 Safe
    </div>
    """, unsafe_allow_html=True)

    alerts = check_expiry_alerts()

    if not alerts:
        st.markdown("""
        <div style='text-align:center; padding:32px; background:#161820; border:1px solid #1e2130;
                    border-radius:14px; color:#6b7280;'>
            🟢 No expiry data available. Upload contracts to begin tracking.
        </div>""", unsafe_allow_html=True)
    else:
        expired_list  = [a for a in alerts if a["status"] == "expired"]
        today_list    = [a for a in alerts if a["status"] == "expires_today"]
        upcoming_list = [a for a in alerts if a["status"] == "upcoming"]
        safe_ct = total - len(expired_list) - len(today_list) - len(upcoming_list)

        a1, a2, a3, a4 = st.columns(4)
        with a1:
            st.markdown(f"""
            <div class='metric-card red'>
                <div class='metric-label'>Expired</div>
                <div class='metric-value'>{len(expired_list)}</div>
                <div class='metric-sub'>Immediate action needed</div>
            </div>""", unsafe_allow_html=True)
        with a2:
            st.markdown(f"""
            <div class='metric-card red'>
                <div class='metric-label'>Expires Today</div>
                <div class='metric-value'>{len(today_list)}</div>
                <div class='metric-sub'>Last chance to renew</div>
            </div>""", unsafe_allow_html=True)
        with a3:
            st.markdown(f"""
            <div class='metric-card amber'>
                <div class='metric-label'>Expiring Soon</div>
                <div class='metric-value'>{len(upcoming_list)}</div>
                <div class='metric-sub'>Prepare renewal</div>
            </div>""", unsafe_allow_html=True)
        with a4:
            st.markdown(f"""
            <div class='metric-card green'>
                <div class='metric-label'>Safe / No Expiry</div>
                <div class='metric-value'>{max(safe_ct, 0)}</div>
                <div class='metric-sub'>No action required</div>
            </div>""", unsafe_allow_html=True)

        st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)

        def render_alert(alert, color):
            fname = alert.get("file_name", "Unknown")
            exp_raw = alert.get("expiry_date", "")
            days = alert.get("days_to_expiry")
            try:
                exp_display = datetime.fromisoformat(exp_raw).strftime("%d %b %Y") if exp_raw else "—"
            except Exception:
                exp_display = exp_raw or "—"

            if days is None:
                days_txt = "Date unparsed"
            elif days < 0:
                days_txt = f"⛔ {abs(days)} day(s) overdue"
            elif days == 0:
                days_txt = "⚠️ Expires TODAY"
            else:
                days_txt = f"⏳ {days} day(s) remaining"

            chex = {"red": "#ef4444", "amber": "#f59e0b", "green": "#22c55e"}.get(color, "#9ba3b8")
            st.markdown(f"""
            <div class='alert-item {color}'>
                <div style='display:flex; justify-content:space-between; align-items:center;'>
                    <div>
                        <div style='font-weight:600; color:#e8eaf0; font-size:0.88rem;'>{fname}</div>
                        <div style='font-size:0.78rem; color:#6b7280; margin-top:2px;'>
                            Expiry: {exp_display}
                        </div>
                    </div>
                    <span style='color:{chex}; font-size:0.82rem; font-weight:600;'>{days_txt}</span>
                </div>
            </div>""", unsafe_allow_html=True)

        if expired_list or today_list:
            st.markdown("""
            <div style='font-size:0.85rem; font-weight:700; color:#ef4444;
                        margin-bottom:10px;'>⛔ Critical — Expired / Expiring Today</div>
            """, unsafe_allow_html=True)
            for a in today_list + expired_list:
                render_alert(a, "red")

        if upcoming_list:
            st.markdown("""
            <div style='font-size:0.85rem; font-weight:700; color:#f59e0b;
                        margin-bottom:10px; margin-top:18px;'>⚠️ Warning — Expiring Soon</div>
            """, unsafe_allow_html=True)
            for a in sorted(upcoming_list, key=lambda x: x.get("days_to_expiry", 9999)):
                render_alert(a, "amber")

    # Full registry table
    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
    st.markdown("""
    <div class='section-title'>
        <span style='color: #9ba3b8;'>◆</span> Full Contract Registry
    </div>""", unsafe_allow_html=True)

    display_cols = ["file_name", "lifecycle_stage", "effective_date", "expiry_date",
                    "party_1_name", "party_2_name", "service_type", "payment_basis"]
    show_cols = [c for c in display_cols if c in df.columns]
    st.dataframe(
        df[show_cols].rename(columns={
            "file_name": "File", "lifecycle_stage": "Stage",
            "effective_date": "Start", "expiry_date": "Expiry",
            "party_1_name": "Party 1", "party_2_name": "Party 2",
            "service_type": "Service", "payment_basis": "Payment"
        }),
        use_container_width=True,
        hide_index=True,
    )

# ═════════════════════════════════════════════════════════════════════════════
# PAGE: ANALYTICS DASHBOARD
# ═════════════════════════════════════════════════════════════════════════════
elif page == "📈 Analytics Dashboard":

    st.markdown("""
    <div style='padding: 8px 0 20px 0;'>
        <div style='font-size: 1.6rem; font-weight: 700; color: #f0f2f6;'>
            Analytics Dashboard
        </div>
        <div style='font-size: 0.88rem; color: #7b8299; margin-top: 3px;'>
            Contract portfolio insights, trends, and risk analysis
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Get all contracts for analytics
    df = get_all_contracts(user_id=st.session_state.user_id, role=st.session_state.role)

    if df.empty:
        st.markdown("""
        <div style='text-align:center; padding:60px; background:#161820; border:1px solid #1e2130;
                    border-radius:14px; color:#6b7280;'>
            <div style='font-size:3rem; margin-bottom:12px;'>📊</div>
            <div style='font-size:1.1rem; color:#9ba3b8; font-weight:600;'>No Data Available</div>
            <div style='font-size:0.88rem; margin-top:8px;'>
                Upload contracts to see analytics insights
            </div>
        </div>""", unsafe_allow_html=True)
        st.stop()

    # ═══════════════════════════════════════════════════════
    # KEY METRICS
    # ═══════════════════════════════════════════════════════

    total_value = get_total_contract_value(st.session_state.user_id, st.session_state.role)
    avg_risk = df['risk_score'].mean() if 'risk_score' in df.columns else 0
    active_count = len(df[df['status'] == 'Active']) if 'status' in df.columns else 0
    expiring_df = get_expiring_contracts(30, st.session_state.user_id, st.session_state.role)
    expiring_count = len(expiring_df)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div class='metric-card blue'>
            <div class='metric-label'>Total Portfolio Value</div>
            <div class='metric-value'>{format_currency(total_value)}</div>
            <div class='metric-sub'>{len(df)} contracts</div>
        </div>""", unsafe_allow_html=True)

    with col2:
        risk_color = "green" if avg_risk < 30 else ("amber" if avg_risk < 70 else "red")
        st.markdown(f"""
        <div class='metric-card {risk_color}'>
            <div class='metric-label'>Average Risk Score</div>
            <div class='metric-value'>{avg_risk:.0f}</div>
            <div class='metric-sub'>{get_risk_category(avg_risk)}</div>
        </div>""", unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class='metric-card green'>
            <div class='metric-label'>Active Contracts</div>
            <div class='metric-value'>{active_count}</div>
            <div class='metric-sub'>{(active_count/len(df)*100):.0f}% of portfolio</div>
        </div>""", unsafe_allow_html=True)

    with col4:
        exp_color = "gray" if expiring_count == 0 else "amber"
        st.markdown(f"""
        <div class='metric-card {exp_color}'>
            <div class='metric-label'>Expiring Soon</div>
            <div class='metric-value'>{expiring_count}</div>
            <div class='metric-sub'>Within 30 days</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════
    # TIME SERIES ANALYSIS
    # ═══════════════════════════════════════════════════════

    st.markdown("""
    <div class='section-title'>
        <span style='color: #9ba3b8;'>📈</span> Trend Analysis
    </div>""", unsafe_allow_html=True)

    monthly_df = get_contracts_by_month(st.session_state.user_id, st.session_state.role)

    if not monthly_df.empty:
        col1, col2 = st.columns(2)

        with col1:
            # Contracts over time
            fig1 = px.line(monthly_df, x='month', y='count',
                          title='Contracts Uploaded Over Time',
                          markers=True)
            fig1.update_layout(
                plot_bgcolor='#1e212c',
                paper_bgcolor='#1e212c',
                font_color='#f0f2f6',
                xaxis_title='Month',
                yaxis_title='Number of Contracts',
                height=400
            )
            st.plotly_chart(fig1, use_container_width=True)

        with col2:
            # Value over time
            fig2 = px.area(monthly_df, x='month', y='total_value',
                          title='Portfolio Value Over Time')
            fig2.update_layout(
                plot_bgcolor='#1e212c',
                paper_bgcolor='#1e212c',
                font_color='#f0f2f6',
                xaxis_title='Month',
                yaxis_title='Total Value (USD)',
                height=400
            )
            st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("📊 Upload contracts across multiple months to see trends")

    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════
    # DISTRIBUTION ANALYSIS
    # ═══════════════════════════════════════════════════════

    st.markdown("""
    <div class='section-title'>
        <span style='color: #9ba3b8;'>🎯</span> Portfolio Distribution
    </div>""", unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        # Risk distribution
        risk_df = get_risk_distribution(st.session_state.user_id, st.session_state.role)
        if not risk_df.empty:
            fig3 = px.pie(risk_df, values='count', names='risk_category',
                         title='Risk Distribution',
                         color='risk_category',
                         color_discrete_map={
                             'Low': '#22c55e',
                             'Medium': '#f59e0b',
                             'High': '#ef4444'
                         })
            fig3.update_layout(
                plot_bgcolor='#1e212c',
                paper_bgcolor='#1e212c',
                font_color='#f0f2f6',
                height=350
            )
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info("No risk data available")

    with col2:
        # Service type distribution
        service_df = get_service_type_distribution(st.session_state.user_id, st.session_state.role)
        if not service_df.empty:
            # Limit to top 5 for readability
            service_df = service_df.head(5)
            fig4 = px.bar(service_df, x='count', y='service_type',
                         title='Top 5 Service Types',
                         orientation='h',
                         color='total_value',
                         color_continuous_scale='Blues')
            fig4.update_layout(
                plot_bgcolor='#1e212c',
                paper_bgcolor='#1e212c',
                font_color='#f0f2f6',
                xaxis_title='Count',
                yaxis_title='Service Type',
                height=350
            )
            st.plotly_chart(fig4, use_container_width=True)
        else:
            st.info("No service type data available")

    with col3:
        # Status distribution
        status_df = get_contracts_by_status(st.session_state.user_id, st.session_state.role)
        if not status_df.empty:
            fig5 = px.pie(status_df, values='count', names='status',
                         title='Status Distribution',
                         hole=0.4)
            fig5.update_layout(
                plot_bgcolor='#1e212c',
                paper_bgcolor='#1e212c',
                font_color='#f0f2f6',
                height=350
            )
            st.plotly_chart(fig5, use_container_width=True)
        else:
            st.info("No status data available")

    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════
    # PARTY ANALYSIS
    # ═══════════════════════════════════════════════════════

    st.markdown("""
    <div class='section-title'>
        <span style='color: #9ba3b8;'>👥</span> Top Contracting Parties
    </div>""", unsafe_allow_html=True)

    parties_df = get_top_parties(st.session_state.user_id, st.session_state.role, limit=10)

    if not parties_df.empty:
        fig6 = px.bar(parties_df, x='count', y='party_name',
                     title='Top 10 Parties by Contract Count',
                     orientation='h',
                     color='total_value',
                     color_continuous_scale='Blues',
                     labels={'count': 'Number of Contracts',
                            'party_name': 'Party Name',
                            'total_value': 'Total Value'})
        fig6.update_layout(
            plot_bgcolor='#1e212c',
            paper_bgcolor='#1e212c',
            font_color='#f0f2f6',
            xaxis_title='Number of Contracts',
            yaxis_title='',
            height=400
        )
        st.plotly_chart(fig6, use_container_width=True)
    else:
        st.info("📊 No party data available yet")

    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════
    # HIGH RISK CONTRACTS
    # ═══════════════════════════════════════════════════════

    st.markdown("""
    <div class='section-title'>
        <span style='color: #9ba3b8;'>⚠️</span> High Risk Contracts
    </div>""", unsafe_allow_html=True)

    if 'risk_score' in df.columns:
        high_risk_df = df[df['risk_score'] > 70].sort_values('risk_score', ascending=False)

        if not high_risk_df.empty:
            # Show relevant columns
            display_cols = []
            if 'file_name' in high_risk_df.columns: display_cols.append('file_name')
            if 'party_1_name' in high_risk_df.columns: display_cols.append('party_1_name')
            if 'party_2_name' in high_risk_df.columns: display_cols.append('party_2_name')
            if 'risk_score' in high_risk_df.columns: display_cols.append('risk_score')
            if 'expiry_date' in high_risk_df.columns: display_cols.append('expiry_date')
            if 'contract_value' in high_risk_df.columns: display_cols.append('contract_value')

            st.dataframe(
                high_risk_df[display_cols],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.success("✅ No high-risk contracts in your portfolio!")
    else:
        st.info("Risk scores not yet calculated. Re-upload contracts to enable risk analysis.")


# ═════════════════════════════════════════════════════════════════════════════
# PAGE: CHAT
# ═════════════════════════════════════════════════════════════════════════════
elif page == "💬 Chat with Contracts":

    st.markdown("""
    <div style='padding: 8px 0 20px 0;'>
        <div style='font-size: 1.6rem; font-weight: 700; color: #f0f2f6;'>
            Chat with Your Contracts
        </div>
        <div style='font-size: 0.88rem; color: #7b8299; margin-top: 3px;'>
            Ask anything — contract clauses, dates, parties, or dashboard stats. Speak naturally.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Build dashboard summary to inject as context for dashboard-level questions
    def build_dashboard_context():
        try:
            df_ctx = get_all_contracts(user_id=st.session_state.user_id, role=st.session_state.role)
            if df_ctx.empty:
                return "No contracts have been uploaded yet."
            lines = [f"Total contracts in the system: {len(df_ctx)}."]
            for _, r in df_ctx.iterrows():
                parts = [f"Contract file: {r.get('file_name','?')}"]
                if r.get("party_1_name"): parts.append(f"Party 1: {r['party_1_name']}")
                if r.get("party_2_name"): parts.append(f"Party 2: {r['party_2_name']}")
                if r.get("effective_date"): parts.append(f"Start: {r['effective_date']}")
                if r.get("expiry_date"):   parts.append(f"Expiry: {r['expiry_date']}")
                if r.get("service_type"):  parts.append(f"Service: {r['service_type']}")
                if r.get("payment_basis"): parts.append(f"Payment: {r['payment_basis']}")
                lines.append(" | ".join(parts))
            alerts = check_expiry_alerts()
            expired = [a["file_name"] for a in alerts if a["status"] == "expired"]
            expiring = [f"{a['file_name']} ({a['days_to_expiry']}d)" for a in alerts if a["status"] == "upcoming"]
            if expired:
                lines.append(f"Expired contracts: {', '.join(expired)}")
            if expiring:
                lines.append(f"Expiring soon: {', '.join(expiring)}")
            return "\n".join(lines)
        except Exception:
            return ""

    if not st.session_state.messages:
        st.markdown("""
        <div style='text-align:center; padding: 40px; background: #1e212c;
                    border: 1.5px dashed #353a50; border-radius: 12px; color: #7b8299;
                    margin-bottom: 20px;'>
            <div style='font-size: 1.8rem; margin-bottom: 10px;'>💬</div>
            <div style='font-size: 0.92rem; color: #c0c4d0; font-weight: 600;'>No conversation yet</div>
            <div style='font-size: 0.82rem; margin-top: 5px;'>
                Try: "When does contract X expire?" or "How many active contracts do we have?"
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        for msg in st.session_state.messages:
            if msg["role"] == "user":
                st.markdown(f"""
                <div style='display:flex; justify-content:flex-end; margin: 5px 0;'>
                    <div class='chat-user'>{msg["content"]}</div>
                </div>""", unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style='display:flex; justify-content:flex-start; margin: 5px 0;'>
                    <div class='chat-assistant'>{msg["content"]}</div>
                </div>""", unsafe_allow_html=True)

    user_question = st.chat_input("Ask about your contracts or dashboard…")

    if user_question:
        st.session_state.messages.append({"role": "user", "content": user_question})

        with st.spinner("Thinking…"):
            # Retrieve vector chunks for contract-level detail
            model = load_model()
            query_embedding = embed_chunks([user_question], model)[0]
            retrieved_chunks = query_similar_chunks(query_embedding)
            vector_context = "\n\n".join([chunk["text"] for chunk in retrieved_chunks])

            # Also inject structured dashboard summary for stats/metrics questions
            dashboard_context = build_dashboard_context()

            combined_context = f"--- DASHBOARD SUMMARY ---\n{dashboard_context}\n\n--- CONTRACT CLAUSES ---\n{vector_context}"
            answer = generate_answer(combined_context, user_question)

        st.session_state.messages.append({"role": "assistant", "content": answer})
        st.rerun()

    if st.session_state.messages:
        if st.button("🗑️ Clear conversation"):
            st.session_state.messages = []
            st.rerun()


# ═════════════════════════════════════════════════════════════════════════════
# PAGE: USER MANAGEMENT (ADMIN ONLY)
# ═════════════════════════════════════════════════════════════════════════════
elif page == "👥 User Management":

    if not is_admin():
        st.error("🚫 Admin access required")
        st.stop()

    st.markdown("""
    <div style='padding: 8px 0 20px 0;'>
        <div style='font-size: 1.6rem; font-weight: 700; color: #f0f2f6;'>
            User Management
        </div>
        <div style='font-size: 0.88rem; color: #7b8299; margin-top: 3px;'>
            Manage user accounts and permissions
        </div>
    </div>
    """, unsafe_allow_html=True)

    users = get_all_users()

    if users:
        st.markdown(f"""
        <div class='metric-card blue' style='margin-bottom: 20px;'>
            <div class='metric-label'>Total Users</div>
            <div class='metric-value'>{len(users)}</div>
            <div class='metric-sub'>Registered accounts</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class='section-title'>
            <span style='color: #9ba3b8;'>👤</span> User List
        </div>""", unsafe_allow_html=True)

        for user in users:
            status_color = "#22c55e" if user['is_active'] else "#ef4444"
            status_text = "Active" if user['is_active'] else "Inactive"

            col1, col2, col3, col4 = st.columns([3, 2, 2, 2])

            with col1:
                st.markdown(f"""
                <div style='padding: 10px 0;'>
                    <div style='font-weight: 600; color: #f0f2f6;'>{user['username']}</div>
                    <div style='font-size: 0.8rem; color: #7b8299;'>{user['email']}</div>
                </div>
                """, unsafe_allow_html=True)

            with col2:
                role_badge = "badge-blue" if user['role'] == "Admin" else "badge-gray"
                st.markdown(f"""
                <div style='padding: 10px 0;'>
                    <span class='badge {role_badge}'>{user['role']}</span>
                </div>
                """, unsafe_allow_html=True)

            with col3:
                st.markdown(f"""
                <div style='padding: 10px 0;'>
                    <span style='color: {status_color}; font-weight: 600;'>● {status_text}</span>
                </div>
                """, unsafe_allow_html=True)

            with col4:
                if user['id'] != st.session_state.user_id:  # Can't modify own account
                    if user['is_active']:
                        if st.button("Deactivate", key=f"deact_{user['id']}", use_container_width=True):
                            if deactivate_user(user['id']):
                                st.success(f"User {user['username']} deactivated")
                                st.rerun()
                    else:
                        if st.button("Activate", key=f"act_{user['id']}", use_container_width=True):
                            if activate_user(user['id']):
                                st.success(f"User {user['username']} activated")
                                st.rerun()

            st.markdown("<div style='border-bottom: 1px solid #2d3140; margin: 10px 0;'></div>", unsafe_allow_html=True)

    else:
        st.info("No users found")
