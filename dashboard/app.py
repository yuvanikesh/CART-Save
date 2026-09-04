"""
CartGuard AI - Streamlit Dashboard
Real-time monitoring dashboard with live sessions, metrics, and audit log.
"""
import streamlit as st
import requests
import json
import time
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sys
import os

# ── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CartGuard AI Dashboard",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")

# ── Custom CSS (aligned to test.html light-mode design) ─────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

    /* Base */
    html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif !important; }
    .main .block-container { background: #f8f9fa; padding-top: 1.5rem; }

    /* Stat card metrics — monospace values */
    [data-testid="stMetricValue"] {
        font-family: 'JetBrains Mono', monospace !important;
        font-weight: 700 !important;
        color: #0f172a !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.78rem !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.4px !important;
        color: #475569 !important;
    }
    [data-testid="stMetricDelta"] { font-size: 0.78rem !important; }

    /* Metric containers — white card style */
    [data-testid="metric-container"] {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 14px 18px !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }

    /* Risk badges */
    .risk-high   { color: #dc2626; font-weight: 700; font-family: 'JetBrains Mono', monospace; }
    .risk-medium { color: #d97706; font-weight: 700; font-family: 'JetBrains Mono', monospace; }
    .risk-low    { color: #059669; font-weight: 700; font-family: 'JetBrains Mono', monospace; }

    /* Action badges */
    .action-badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 5px;
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.3px;
    }
    .badge-rose    { background: #fef2f2; color: #dc2626; }
    .badge-amber   { background: #fffbeb; color: #d97706; }
    .badge-emerald { background: #ecfdf5; color: #059669; }
    .badge-blue    { background: #f0f9ff; color: #0284c7; }
    .badge-violet  { background: #f5f3ff; color: #7c3aed; }

    /* Primary button */
    .stButton > button {
        background: #1e293b !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 10px 24px !important;
        font-weight: 700 !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        transition: opacity 0.2s ease !important;
    }
    .stButton > button:hover { opacity: 0.88 !important; }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: #ffffff !important;
        border-right: 1px solid #e2e8f0 !important;
    }
    [data-testid="stSidebar"] * { color: #0f172a !important; }

    .sidebar-header {
        background: #1e293b;
        padding: 14px 16px;
        border-radius: 10px;
        text-align: center;
        color: white !important;
        font-weight: 700;
        font-size: 1rem;
        margin-bottom: 18px;
        letter-spacing: 0.2px;
    }

    /* Evidence items */
    .evidence-item {
        font-size: 0.85rem;
        color: #475569;
        padding: 9px 13px;
        background: #f8fafc;
        border-left: 3px solid #1e293b;
        border-radius: 0 6px 6px 0;
        margin-bottom: 8px;
        line-height: 1.45;
    }

    /* Dividers */
    hr { border-color: #e2e8f0 !important; }

    /* Audit table */
    [data-testid="stDataFrame"] {
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        overflow: hidden;
    }
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────
def api_call(endpoint: str, method: str = "GET", data: dict = None):
    try:
        url = f"{API_BASE}{endpoint}"
        if method == "GET":
            r = requests.get(url, timeout=10)
        else:
            r = requests.post(url, json=data, timeout=15)
        if r.status_code == 200:
            return r.json()
        return None
    except Exception as e:
        return None


def risk_color(level: str) -> str:
    return {"HIGH": "#ff4757", "MEDIUM": "#ffa502", "LOW": "#2ed573"}.get(level, "#999")


def action_color(action: str) -> str:
    colors = {
        "DO_NOTHING": "#636e72",
        "ALTERNATE_PAYMENT_GUIDANCE": "#0984e3",
        "SOCIAL_PROOF_NUDGE": "#6c5ce7",
        "CHECKOUT_ASSISTANCE": "#00b894",
        "LIMITED_OFFER": "#e17055",
    }
    return colors.get(action, "#74b9ff")


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sidebar-header">🛒 CartGuard AI 7-Agent System</div>', unsafe_allow_html=True)
    
    page = st.selectbox(
        "Navigation",
        [
            "🏠 Executive Dashboard",
            "🤖 7-Agent Pipeline Inspector",
            "🛡️ HITL Command Center",
            "🔄 Closed-Loop Memory & Rules",
            "🔬 Score Session",
            "⚡ Batch Scoring",
            "🎭 Demo Scenarios",
            "📋 Microsecond Audit Ledger"
        ],
    )
    
    st.divider()
    
    # Health check
    health = api_call("/health")
    if health:
        st.success("✅ 7-Agent Backend Connected")
    else:
        st.error("❌ Backend Offline")
        st.info("Start backend: `python backend/main.py`")
    
    st.divider()
    st.markdown("**Enterprise Specs**")
    st.caption("⚡ Fast ML Filter: <5ms Pass-Through")
    st.caption("🧠 Head Controller: Max 2 Iterations")
    st.caption("🛡️ HITL Gate: Single-Click >₹50k Sign-Off")
    st.caption("🔒 Audit Ledger: Microsecond Step Logs")
    
    auto_refresh = st.checkbox("Auto-refresh (10s)", value=False)
    if auto_refresh:
        time.sleep(10)
        st.rerun()


# ── Executive Dashboard Page ───────────────────────────────────────────────────
if "🏠 Executive Dashboard" in page or page == "🏠 Dashboard":

    st.title("🛒 CartGuard AI — Real-Time Dashboard")
    st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")
    
    metrics = api_call("/api/v1/metrics")
    
    if metrics:
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric("Total Sessions", metrics.get("total_sessions", 0))
        with col2:
            st.metric("High Risk", metrics.get("high_risk_sessions", 0),
                      delta=f"{metrics.get('high_risk_sessions',0)/max(metrics.get('total_sessions',1),1)*100:.0f}%")
        with col3:
            st.metric("Actions Taken", metrics.get("actions_taken", 0))
        with col4:
            st.metric("DO NOTHING Rate", f"{metrics.get('do_nothing_rate', 0):.0f}%")
        with col5:
            st.metric("Avg Latency", f"{metrics.get('avg_latency_ms', 0):.0f}ms")

        st.divider()
        
        col_l, col_r = st.columns(2)
        
        with col_l:
            # Cause distribution
            cause_dist = metrics.get("cause_distribution", {})
            if cause_dist:
                fig = px.pie(
                    values=list(cause_dist.values()),
                    names=list(cause_dist.keys()),
                    title="Abandonment Root Cause Distribution",
                    color_discrete_sequence=px.colors.qualitative.Bold,
                    hole=0.4,
                )
                fig.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font_color="white",
                )
                st.plotly_chart(fig, use_container_width=True)
        
        with col_r:
            # Action distribution
            action_dist = metrics.get("action_distribution", {})
            if action_dist:
                fig = px.bar(
                    x=list(action_dist.values()),
                    y=list(action_dist.keys()),
                    orientation="h",
                    title="Action Distribution",
                    color=list(action_dist.keys()),
                    color_discrete_sequence=px.colors.qualitative.Pastel,
                )
                fig.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font_color="white",
                    showlegend=False,
                )
                st.plotly_chart(fig, use_container_width=True)

        # Financial metrics
        st.subheader("💰 Financial Impact")
        f1, f2, f3, f4 = st.columns(4)
        with f1:
            st.metric("Total Discount Spent", f"₹{metrics.get('total_discount_inr', 0):,.0f}")
        with f2:
            st.metric("Avg Discount/Action", f"₹{metrics.get('avg_discount_per_action_inr', 0):.0f}")
        with f3:
            st.metric("AI Cost/Decision", f"₹{metrics.get('cost_per_decision_inr', 0):.4f}")
        with f4:
            st.metric("Total AI Cost", f"₹{metrics.get('total_ai_cost_inr', 0):.2f}")
    else:
        st.info("📊 No metrics yet. Run the demo scenarios to populate the dashboard!")
        
        # Show architecture diagram
        st.subheader("🏗️ System Architecture")
        st.code("""
Browser SDK → WebSocket → FastAPI Orchestrator
                                    │
        ┌───────────────────────────┼────────────────────────┐
        ▼                           ▼                        ▼
Signal Agent               Risk Agent (ML)          Context Agent
(Derive micro-signals)     CatBoost+XGBoost         (LTV, Segment)
        │                           │
        └───────────────────────────┘
                        │
                        ▼
            Diagnosis Agent (LLM)
            PaymentFailure / Friction / Comparison
                        │
                        ▼
            Policy & Guardrail Agent
            Budget / Consent / Uplift
                        │
                        ▼
            Action Agent (Generative LLM)
            Personalized nudge / DO_NOTHING
                        │
                        ▼
            Self-Check Agent (Validator)
            Consistency / Budget / Margin
                        │
                        ▼
            Audit Log (SQLite → PostgreSQL)
        """, language="text")



# ── 7-Agent Pipeline Inspector Page ──────────────────────────────────────────
elif "🤖 7-Agent Pipeline Inspector" in page:
    st.title("🤖 7-Agent Enterprise Pipeline Inspector")
    st.caption("Live node-by-node execution trace, latency Breakdown, and Adversarial Auditor verification.")

    with st.expander("⚙️ Session Test Configuration", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            test_cart_value = st.number_input("Cart Value (₹)", 100.0, 100000.0, 4800.0, step=500.0)
            test_attempts = st.slider("Payment Attempts", 0, 5, 2)
            test_failures = st.slider("Payment Failures", 0, 5, 2)
        with col2:
            test_duration = st.slider("Session Duration (s)", 30, 1200, 240)
            test_tab_switches = st.slider("Tab Switches", 0, 15, 4)
            test_form_errors = st.slider("Form Field Errors", 0, 10, 1)
        with col3:
            test_user_segment = st.selectbox("User Segment", ["REGULAR", "PREMIUM", "BARGAIN"])
            test_user_spend = st.number_input("Discount Spend This Month (₹)", 0.0, 500.0, 0.0)
            test_is_b2b = st.checkbox("B2B Invoice Transaction", value=False)

    if st.button("🚀 Run 7-Agent Pipeline", use_container_width=True):
        payload = {
            "session_id": f"TEST-{int(time.time())}",
            "user_id": "USR-INSPECTOR",
            "cart_value": test_cart_value,
            "session_duration": test_duration,
            "payment_attempts": test_attempts,
            "payment_failures": test_failures,
            "tab_loss_count": test_tab_switches,
            "form_field_errors": test_form_errors,
            "user_segment": test_user_segment,
            "user_discount_spend_this_month": test_user_spend,
            "is_b2b": test_is_b2b,
        }

        with st.spinner("⚡ Running 7-Agent Pipeline..."):
            res = api_call("/api/v1/score", method="POST", data=payload)

        if res:
            st.success(f"✅ Pipeline Executed in {res.get('metrics', {}).get('total_latency_ms', 0)}ms")

            # 7 Nodes Visual Trace
            st.subheader("📌 7-Agent Pipeline Execution Trace")
            step_logs = res.get("step_logs", [])
            
            for step in step_logs:
                node_num = step.get("step")
                node_name = step.get("node")
                status = step.get("status")
                lat = step.get("latency_ms")
                details = step.get("details", "")

                status_color = "🟢" if "PASSED" in status or "APPROVED" in status or "ROUTED" in status or "DIAGNOSED" in status or "PROFILED" in status or "PROPOSED" in status or "AUTO" in status else "🟡"
                st.markdown(f"**Step {node_num}: {node_name}** {status_color} `{status}` — *{lat:.2f}ms*")
                st.caption(f"↳ {details}")
                st.divider()

            # Output Cards
            col_a, col_b = st.columns(2)
            with col_a:
                st.subheader("🎯 Prescribed Strategy")
                act = res.get("action", {})
                st.info(f"**Action:** `{act.get('proposed_action', act.get('action_type'))}`\n\n**Channel:** `{act.get('channel')}`\n\n**Discount:** ₹{act.get('discount_amount', 0)}\n\n**Message:** {act.get('message')}")
            
            with col_b:
                st.subheader("🛡️ Adversarial Audit & HITL")
                audit = res.get("adversarial_audit", {})
                hitl = res.get("hitl_gate", {})
                st.write(f"**Auditor Status:** `{audit.get('status')}` (Confidence: {audit.get('auditor_confidence')})")
                st.write(f"**Requires HITL:** `{hitl.get('requires_hitl')}` ({hitl.get('hitl_reason')})")
                if audit.get("warnings"):
                    st.warning(f"Warnings: {audit.get('warnings')}")
                if audit.get("rejections"):
                    st.error(f"Rejections: {audit.get('rejections')}")

            with st.expander("🔍 Complete Response Payload"):
                st.json(res)


# ── HITL Command Center Page ──────────────────────────────────────────────────
elif "🛡️ HITL Command Center" in page:
    st.title("🛡️ Human-in-the-Loop (HITL) Gate")
    st.caption("Single-click human review for transactions >₹50,000 or low auditor confidence.")

    hitl_data = api_call("/api/v1/hitl/pending")

    if hitl_data and hitl_data.get("pending_reviews"):
        pending = hitl_data["pending_reviews"]
        st.warning(f"⚠️ {len(pending)} Transactions Pending Human Sign-Off")

        for idx, item in enumerate(pending):
            with st.expander(f"🛒 **{item['session_id']}** — Cart Value: ₹{item.get('discount_amount', 0)*10:,.0f} | Risk: {item['risk_score']:.0%}", expanded=True):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"**User ID:** `{item['user_id']}`")
                    st.markdown(f"**Root Cause:** `{item['root_cause']}`")
                    st.markdown(f"**Proposed Action:** `{item['proposed_action']}` (Discount: ₹{item['discount_amount']})")
                    st.markdown(f"**HITL Trigger Reason:** `{item['hitl_reason']}`")
                
                with col2:
                    notes = st.text_input("Review Notes", key=f"notes_{item['session_id']}")
                    c_app, c_rej = st.columns(2)
                    with c_app:
                        if st.button("✅ Approve", key=f"app_{item['session_id']}"):
                            res = api_call("/api/v1/hitl/approve", method="POST", data={"session_id": item['session_id'], "notes": notes})
                            if res:
                                st.success("Approved!")
                                st.rerun()
                    with c_rej:
                        if st.button("❌ Reject", key=f"rej_{item['session_id']}"):
                            res = api_call("/api/v1/hitl/reject", method="POST", data={"session_id": item['session_id'], "notes": notes})
                            if res:
                                st.error("Rejected!")
                                st.rerun()
    else:
        st.success("✅ No pending reviews in HITL queue. All transactions auto-approved by 7-agent guardrails!")


# ── Closed-Loop Memory Page ───────────────────────────────────────────────────
elif "🔄 Closed-Loop Memory & Rules" in page:
    st.title("🔄 Closed-Loop Memory & LangChain Guardrails Engine")
    st.caption("Inspect Tool-Augmented Empirical Outcome Memory, Margin Elasticity, and Statutory Guardrails.")

    st.subheader("🔍 Tool-Augmented Experience & Analytics Retrieval")
    st.caption("Executes `query_historical_policy_outcomes_tool` to pull historical conversion rates, opt-out risks, and minimum effective discount baselines.")

    e1, e2, e3 = st.columns(3)
    with e1:
        q_profile = st.selectbox("Psych Profile", ["SECURITY_CONSCIOUS", "PRICE_SENSITIVE", "DECISION_PARALYSIS"])
    with e2:
        q_action = st.selectbox("Proposed Action", ["LIMITED_OFFER", "ALTERNATE_PAYMENT_GUIDANCE", "SCARCITY_SOCIAL_PROOF", "ONE_CLICK_CLARITY"])
    with e3:
        q_discount = st.slider("Proposed Discount %", 0.0, 20.0, 5.0, step=0.5)

    outcomes_res = api_call(f"/api/v1/auditor/policy-outcomes?psych_profile={q_profile}&proposed_action={q_action}&discount_pct={q_discount}")

    if outcomes_res and "outcomes" in outcomes_res:
        out = outcomes_res["outcomes"]
        st.info(f"**Historical Verdict:** `{out.get('historical_verdict')}`\n\n**Summary:** {out.get('summary')}")

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("Sample Size", out.get("sample_size", 0))
        with m2:
            st.metric("Historical Recovery Rate", f"{out.get('recovery_rate', 0):.0%}")
        with m3:
            st.metric("Opt-Out / Spam Rate", f"{out.get('opt_out_rate', 0):.1%}", delta="Spam Flag (>15%) ⚠️" if out.get("opt_out_rate", 0) > 0.15 else "Low Risk ✅")
        with m4:
            st.metric("Min Effective Discount", f"{out.get('min_effective_discount_pct', 0):.1f}%", delta="Over-Discounting ⚠️" if out.get("over_discount_flag") else "Optimal Rate ✅")

    st.divider()

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🛡️ Active Hard Guardrails")
        st.markdown("""
        - **Gross Margin Floor**: Net margin remaining must be $\ge 15\%$ of cart value.
        - **TRAI DND Window**: Direct SMS/WhatsApp permitted only between **8:00 AM - 9:00 PM IST**.
        - **RBI E-Mandate Cooldown**: Mandatory 24-hour interval between retrying failed auto-debits.
        - **User Budget Cap**: Maximum **₹500 / month** per user.
        - **Campaign Budget Cap**: Maximum **₹50,000** global campaign spend limit.
        """)

    with c2:
        st.subheader("📝 Record Outcome Feedback")
        fb_session = st.text_input("Session ID", "SES-YUVA-9912")
        fb_outcome = st.selectbox("Actual Outcome", ["RECOVERED", "OPT_OUT", "CONVERTED", "ABANDONED"])
        if st.button("💾 Record Outcome Feedback"):
            res = api_call("/api/v1/feedback", method="POST", data={"session_id": fb_session, "outcome": fb_outcome})
            if res:
                st.success(f"Feedback recorded for `{fb_session}`: {fb_outcome}")



# ── Score Session Page ─────────────────────────────────────────────────────────

elif "🔬 Score Session" in page:
    st.title("🔬 Score a Session")
    st.caption("Enter session data to get real-time abandonment risk score and recommended action.")

    with st.form("session_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Session Behavior")
            session_duration = st.slider("Session Duration (seconds)", 0, 1800, 300)
            product_views = st.slider("Product Views", 0, 50, 5)
            cart_adds = st.slider("Cart Adds", 0, 20, 2)
            cart_removes = st.slider("Cart Removes", 0, 10, 0)
            cart_value = st.number_input("Cart Value (₹)", 0.0, 50000.0, 1500.0, step=100.0)
            category_switches = st.slider("Category Switches", 0, 10, 2)
            tab_switches = st.slider("Tab Switches", 0, 20, 3)
        
        with col2:
            st.subheader("Checkout & Payment")
            checkout_steps = st.slider("Checkout Steps Completed (of 5)", 0, 5, 2)
            checkout_time = st.slider("Checkout Time (seconds)", 0, 600, 60)
            payment_attempts = st.slider("Payment Attempts", 0, 5, 0)
            payment_failures = st.slider("Payment Failures", 0, 5, 0)
            time_on_payment = st.slider("Time on Payment Page (seconds)", 0, 600, 0)
            form_errors = st.slider("Form Field Errors", 0, 10, 0)
            back_navs = st.slider("Back Navigations", 0, 10, 1)
        
        col3, col4 = st.columns(2)
        with col3:
            st.subheader("User Profile")
            is_returning = st.checkbox("Returning Visitor", value=True)
            user_segment = st.selectbox("User Segment", ["REGULAR", "PREMIUM", "BARGAIN", "NEW"])
            user_spend_month = st.number_input("Discount Spend This Month (₹)", 0.0, 500.0, 0.0)
        
        with col4:
            st.subheader("Consent")
            is_dnd = st.checkbox("DND Registered", value=False)
            email_opt = st.checkbox("Email Opt-In", value=True)
            sms_opt = st.checkbox("SMS Opt-In", value=True)
            user_email = st.text_input("User Email (optional)", "")
        
        submitted = st.form_submit_button("🚀 Score Session", use_container_width=True)
    
    if submitted:
        payload = {
            "session_id": f"MANUAL_{int(time.time())}",
            "session_duration": session_duration,
            "product_views": product_views,
            "cart_adds": cart_adds,
            "cart_removes": cart_removes,
            "cart_changes": cart_adds + cart_removes,
            "cart_value": cart_value,
            "category_switches": category_switches,
            "tab_switches": tab_switches,
            "checkout_steps_completed": checkout_steps,
            "checkout_time": checkout_time,
            "payment_attempts": payment_attempts,
            "payment_failures": payment_failures,
            "time_on_payment_page": time_on_payment,
            "form_field_errors": form_errors,
            "back_navigations": back_navs,
            "is_returning_visitor": is_returning,
            "user_segment": user_segment,
            "user_discount_spend_this_month": user_spend_month,
            "is_dnd_registered": is_dnd,
            "email_opt_in": email_opt,
            "sms_opt_in": sms_opt,
            "user_email": user_email,
        }
        
        with st.spinner("⚡ Scoring session through AI agents..."):
            result = api_call("/api/v1/score", method="POST", data=payload)
        
        if result:
            risk_score = result.get("risk_score", 0)
            risk_level = result.get("risk_level", "LOW")
            
            # Risk gauge
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                fig = go.Figure(go.Indicator(
                    mode="gauge+number+delta",
                    value=risk_score * 100,
                    domain={"x": [0, 1], "y": [0, 1]},
                    title={"text": f"Abandonment Risk — {risk_level}", "font": {"size": 20}},
                    gauge={
                        "axis": {"range": [0, 100]},
                        "bar": {"color": risk_color(risk_level)},
                        "steps": [
                            {"range": [0, 35], "color": "#1a2a1a"},
                            {"range": [35, 55], "color": "#2a2a1a"},
                            {"range": [55, 75], "color": "#2a1a1a"},
                            {"range": [75, 100], "color": "#3a1a1a"},
                        ],
                        "threshold": {
                            "line": {"color": "white", "width": 3},
                            "thickness": 0.75,
                            "value": risk_score * 100,
                        },
                    },
                ))
                fig.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    font_color="white",
                    height=300,
                )
                st.plotly_chart(fig, use_container_width=True)
            
            # Diagnosis
            st.subheader("🩺 Diagnosis")
            diag = result.get("diagnosis", {})
            dcol1, dcol2 = st.columns(2)
            with dcol1:
                st.markdown(f"**Root Cause:** `{diag.get('root_cause', 'UNKNOWN')}`")
                st.markdown(f"**Confidence:** {diag.get('confidence', 0)*100:.0f}%")
            with dcol2:
                st.markdown("**Evidence:**")
                for e in diag.get("evidence", []):
                    st.markdown(f"- {e}")
            
            # Action
            action = result.get("action", {})
            st.subheader("⚡ Recommended Action")
            acol1, acol2 = st.columns([1, 2])
            with acol1:
                action_type = action.get("action_type", "DO_NOTHING")
                color = action_color(action_type)
                st.markdown(
                    f'<span style="background:{color};color:white;padding:8px 16px;'
                    f'border-radius:20px;font-weight:700;font-size:14px;">'
                    f'{action_type}</span>',
                    unsafe_allow_html=True,
                )
                if action.get("discount_amount", 0) > 0:
                    st.metric("Discount", f"₹{action['discount_amount']:.0f}")
            with acol2:
                if action.get("message"):
                    st.info(f"💬 {action.get('message', '')}")
                st.caption(f"📢 Channel: {action.get('channel', 'IN_APP')}")
            
            # Self-check
            self_check = result.get("self_check", {})
            if self_check.get("status") == "PASSED":
                st.success("✅ Self-Check: PASSED — All guardrails satisfied")
            else:
                st.error(f"❌ Self-Check: FAILED — Action overridden to DO_NOTHING")
            
            # Signals
            with st.expander("📊 Behavioral Signals"):
                signals = result.get("signals", {})
                sig_df = pd.DataFrame([
                    {"Signal": k, "Value": v, "Interpretation": _interpret_signal(k, v)}
                    for k, v in signals.items()
                ])
                st.dataframe(sig_df, use_container_width=True)
            
            # Metrics
            with st.expander("⏱️ Performance Metrics"):
                metrics_data = result.get("metrics", {})
                mcol1, mcol2, mcol3 = st.columns(3)
                mcol1.metric("Total Latency", f"{metrics_data.get('total_latency_ms', 0):.0f}ms")
                mcol2.metric("AI Cost", f"₹{metrics_data.get('total_cost_inr', 0):.4f}")
                
                agent_latencies = metrics_data.get("agent_latencies", {})
                if agent_latencies:
                    fig = px.bar(
                        x=list(agent_latencies.keys()),
                        y=list(agent_latencies.values()),
                        title="Agent Latency Breakdown",
                        labels={"x": "Agent", "y": "Latency (ms)"},
                        color=list(agent_latencies.values()),
                        color_continuous_scale="viridis",
                    )
                    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font_color="white")
                    st.plotly_chart(fig, use_container_width=True)
            
            # Full JSON
            with st.expander("🔍 Full Result JSON"):
                st.json(result)
        else:
            st.error("Failed to score session. Is the backend running?")


# ── Batch Scoring Page ────────────────────────────────────────────────────────
elif "⚡ Batch Scoring" in page:
    st.title("⚡ Batch Session Scoring")
    st.caption("Score multiple sessions in parallel via `POST /api/v1/score/batch`.")

    mode = st.radio("Select Batch Source", ["🎭 6 PRD Demo Scenarios Batch", "🎲 Generate Random Sessions Batch"], horizontal=True)

    if "6 PRD" in mode:
        scenarios_data = api_call("/api/v1/demo/scenarios")
        if scenarios_data and "scenarios" in scenarios_data:
            sessions_list = [s["session_data"] for s in scenarios_data["scenarios"]]
            st.info(f"Loaded {len(sessions_list)} pre-configured demo scenarios for parallel batch execution.")
        else:
            sessions_list = [
                {"session_id": "BATCH_001", "cart_value": 3500, "payment_attempts": 2, "payment_failures": 1, "session_duration": 240},
                {"session_id": "BATCH_002", "cart_value": 1200, "product_views": 12, "tab_switches": 8, "session_duration": 480},
                {"session_id": "BATCH_003", "cart_value": 800, "form_field_errors": 5, "session_duration": 360},
                {"session_id": "BATCH_004", "cart_value": 1500, "payment_attempts": 2, "payment_failures": 1, "session_duration": 300},
                {"session_id": "BATCH_005", "cart_value": 0, "product_views": 15, "session_duration": 720},
                {"session_id": "BATCH_006", "cart_value": 900, "cart_adds": 3, "cart_removes": 2, "session_duration": 180},
            ]
            st.caption("Using offline fallback session payloads.")
    else:
        batch_size = st.slider("Batch Size", 2, 20, 5)
        sessions_list = []
        for i in range(batch_size):
            sessions_list.append({
                "session_id": f"RAND_BATCH_{i+1:03d}",
                "cart_value": float(np.random.randint(500, 5000)),
                "session_duration": float(np.random.randint(60, 600)),
                "product_views": int(np.random.randint(1, 15)),
                "cart_adds": int(np.random.randint(1, 5)),
                "payment_attempts": int(np.random.randint(0, 3)),
                "payment_failures": int(np.random.randint(0, 2)),
            })
        st.write(f"Generated {len(sessions_list)} dynamic random session payloads.")

    with st.expander("🔍 Inspect Batch Request Payload"):
        st.json({"sessions": sessions_list})

    if st.button("🚀 Execute Batch Scoring", use_container_width=True):
        with st.spinner(f"⚡ Scoring {len(sessions_list)} sessions in parallel..."):
            res = api_call("/api/v1/score/batch", method="POST", data={"sessions": sessions_list})

        if res and "results" in res:
            results = res["results"]
            st.success(f"✅ Processed {res.get('total', len(results))} sessions in parallel.")

            # Summary Metrics
            col1, col2, col3, col4 = st.columns(4)
            high_risk = sum(1 for r in results if r.get("risk_level") == "HIGH")
            do_nothing = sum(1 for r in results if r.get("action", {}).get("action_type") == "DO_NOTHING")
            avg_lat = np.mean([r.get("metrics", {}).get("total_latency_ms", 0) for r in results if "metrics" in r]) if results else 0

            with col1:
                st.metric("Total Scored", len(results))
            with col2:
                st.metric("High Risk Sessions", high_risk)
            with col3:
                st.metric("DO NOTHING Rate", f"{(do_nothing / max(len(results), 1)) * 100:.0f}%")
            with col4:
                st.metric("Avg Latency", f"{avg_lat:.0f}ms")

            # Table display
            table_data = []
            for r in results:
                if "error" in r:
                    table_data.append({"Session ID": "Error", "Risk Score": "N/A", "Risk Level": "ERROR", "Root Cause": r.get("error"), "Action": "NONE", "Latency": "N/A"})
                else:
                    table_data.append({
                        "Session ID": r.get("session_id", "N/A"),
                        "Risk Score": f"{r.get('risk_score', 0):.0%}",
                        "Risk Level": r.get("risk_level", "LOW"),
                        "Root Cause": r.get("diagnosis", {}).get("root_cause", "N/A"),
                        "Action": r.get("action", {}).get("action_type", "DO_NOTHING"),
                        "Discount": f"₹{r.get('action', {}).get('discount_amount', 0):.0f}",
                        "Self Check": r.get("self_check", {}).get("status", "N/A"),
                        "Latency (ms)": f"{r.get('metrics', {}).get('total_latency_ms', 0):.0f}",
                    })

            st.subheader("📋 Batch Results Summary")
            st.dataframe(pd.DataFrame(table_data), use_container_width=True)

            with st.expander("🔍 Full Batch Response JSON"):
                st.json(res)
        else:
            st.error("Failed to execute batch scoring. Is backend running at `http://localhost:8000`?")


# ── Demo Scenarios Page ─────────────────────────────────────────────────────────
elif "🎭 Demo Scenarios" in page:
    st.title("🎭 Demo Scenarios")
    st.caption("Run pre-built scenarios from the PRD to showcase CartGuard AI capabilities.")
    
    scenarios_data = api_call("/api/v1/demo/scenarios")
    
    if not scenarios_data:
        st.error("Backend not connected. Start the backend first.")
    else:
        scenarios = scenarios_data.get("scenarios", [])
        
        for i, scenario in enumerate(scenarios):
            with st.expander(f"**{i+1}. {scenario['name'].upper().replace('_', ' ')}** — {scenario['description']}"):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.caption(f"Expected: `{scenario.get('expected', 'See result')}`")
                with col2:
                    if st.button(f"▶ Run", key=f"demo_{scenario['name']}"):
                        with st.spinner(f"Running {scenario['name']}..."):
                            result = api_call(f"/api/v1/demo/run/{scenario['name']}", method="POST")
                        
                        if result:
                            res = result.get("result", {})
                            risk = res.get("risk_score", 0)
                            action = res.get("action", {}).get("action_type", "?")
                            diag = res.get("diagnosis", {}).get("root_cause", "?")
                            
                            st.success(f"✅ Risk: {risk:.0%} | Diagnosis: {diag} | Action: {action}")
                            
                            if action == scenario.get("expected"):
                                st.balloons()
                                st.success(f"🎯 Action matches expected: `{action}`")
                            else:
                                st.warning(f"⚠️ Expected `{scenario.get('expected')}` but got `{action}`")
                            
                            with st.expander("Full Result"):
                                st.json(res)


# ── Uplift Analysis Page ──────────────────────────────────────────────────────
elif "📊 Uplift Analysis" in page:
    st.title("📊 Synthetic Uplift Analysis")
    st.caption("Prove incremental margin impact with statistical significance.")
    
    col1, col2 = st.columns(2)
    with col1:
        n_sessions = st.select_slider("Simulation Size", [1000, 5000, 10000, 50000], value=10000)
    with col2:
        if st.button("▶ Run Simulation", use_container_width=True):
            with st.spinner("Running uplift simulation..."):
                import sys
                sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
                try:
                    from services.uplift_service import uplift_simulator
                    result = uplift_simulator.simulate_ab_test(n_sessions=n_sessions)
                    st.session_state["uplift_result"] = result
                except Exception as e:
                    st.error(f"Error: {e}")
    
    if "uplift_result" in st.session_state:
        result = st.session_state["uplift_result"]
        
        cvr = result.get("conversion_rates", {})
        sig = result.get("statistical_significance", {})
        fin = result.get("financial_impact", {})
        
        # Key metrics
        st.subheader("📈 Conversion Rate Results")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Control CVR", f"{cvr.get('control_cvr', 0):.1f}%")
        m2.metric("Treatment CVR", f"{cvr.get('treatment_cvr', 0):.1f}%",
                  delta=f"+{cvr.get('absolute_uplift_pp', 0):.1f}pp")
        m3.metric("Relative Uplift", f"{cvr.get('relative_uplift_pct', 0):.1f}%")
        m4.metric("p-value", f"{sig.get('p_value', 1):.4f}",
                  delta="Significant ✅" if sig.get("is_significant") else "Not significant ❌")
        
        # Financial impact
        st.subheader("💰 Financial Impact")
        f1, f2, f3 = st.columns(3)
        f1.metric("Incremental Margin/Session", f"₹{fin.get('incremental_margin_per_session_inr', 0):.2f}")
        f2.metric("Discount Reduction", f"{fin.get('discount_reduction_pct', 0):.0f}%")
        f3.metric("Smart vs Blanket Savings", f"₹{fin.get('discount_savings_per_session_inr', 0):.2f}")
        
        # CI visualization
        st.subheader("📊 Confidence Interval for Uplift")
        ci_low = cvr.get("ci_lower_pp", 0)
        ci_high = cvr.get("ci_upper_pp", 0)
        uplift_val = cvr.get("absolute_uplift_pp", 0)
        
        fig = go.Figure()
        fig.add_shape(type="rect", x0=ci_low, x1=ci_high, y0=0.3, y1=0.7,
                      fillcolor="rgba(102,126,234,0.3)", line_color="rgba(102,126,234,0.8)")
        fig.add_vline(x=uplift_val, line_color="#764ba2", line_width=3)
        fig.add_vline(x=0, line_color="white", line_dash="dash")
        fig.update_layout(
            title=f"95% CI for Uplift: [{ci_low:.1f}pp, {ci_high:.1f}pp]",
            xaxis_title="Conversion Rate Uplift (percentage points)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="white",
            height=200,
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Action performance
        st.subheader("🎯 Action Performance")
        action_perf = result.get("action_performance", {})
        if action_perf:
            perf_df = pd.DataFrame([
                {"Action": k, "Count": v["count"], "CVR%": v["cvr"],
                 "Avg Margin ₹": v["avg_margin_inr"], "Avg Discount ₹": v["avg_discount_inr"]}
                for k, v in action_perf.items()
            ])
            st.dataframe(perf_df, use_container_width=True)


# ── Audit Log Page ─────────────────────────────────────────────────────────────
elif "📋 Audit Log" in page:
    st.title("📋 Audit Log")
    st.caption("Full decision trail with evidence chains for every session.")
    
    col1, col2 = st.columns(2)
    with col1:
        limit = st.selectbox("Show last N entries", [10, 25, 50, 100], index=1)
    with col2:
        filter_session = st.text_input("Filter by Session ID", "")
    
    # Bug fix: pass session filter to API call
    audit_endpoint = f"/api/v1/audit?limit={limit}"
    if filter_session:
        audit_endpoint += f"&session_id={filter_session}"
    logs = api_call(audit_endpoint)
    
    if logs and logs.get("logs"):
        df = pd.DataFrame(logs["logs"])
        
        display_cols = [
            "timestamp", "session_id", "risk_score", "risk_level",
            "root_cause", "action_type", "discount_amount",
            "self_check_status", "total_latency_ms", "total_cost_inr"
        ]
        available_cols = [c for c in display_cols if c in df.columns]
        
        st.dataframe(df[available_cols], use_container_width=True)
        
        # Download
        csv = df.to_csv(index=False)
        st.download_button("⬇️ Download CSV", csv, "audit_log.csv", "text/csv")
    else:
        st.info("No audit entries yet. Score some sessions to populate the log.")


# ── Signal Interpreter — moved above first use to fix NameError ──────────────
def _interpret_signal(signal: str, value: float) -> str:
    """Interpret a 0–1 signal value as a human-readable label."""
    interpretations = {
        "hesitation_score":  ["Decisive", "Slightly hesitant", "Hesitant", "Very hesitant"],
        "price_sensitivity": ["Not price-sensitive", "Slightly price-sensitive", "Price-sensitive", "Highly price-sensitive"],
        "funnel_friction":   ["Smooth journey", "Minor friction", "Significant friction", "Severe friction"],
        "comparison_intent": ["Focused buyer", "Some comparison", "Active comparison", "Heavy comparison"],
        "urgency_score":     ["Low urgency", "Moderate urgency", "High urgency", "Very urgent"],
        "payment_risk":      ["No payment risk", "Low risk", "Medium risk", "High payment risk"],
    }
    labels = interpretations.get(signal, ["Low", "Medium", "High", "Very High"])
    idx = min(int(value * 4), 3)
    return labels[idx]


if __name__ == "__main__":
    pass
