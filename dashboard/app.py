"""EvalForge Streamlit Dashboard"""

import os
import asyncio
import json
from datetime import datetime

import httpx
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ============================================================
# CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="EvalForge",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Premium Custom CSS Injection for Glassmorphism & Micro-animations
st.markdown(
    """
    <div style="position: fixed; top: -120px; left: -120px; width: 400px; height: 400px; background: rgba(99, 102, 241, 0.12); filter: blur(120px); border-radius: 50%; pointer-events: none; z-index: -1;"></div>
    <div style="position: fixed; bottom: -120px; right: -120px; width: 500px; height: 500px; background: rgba(6, 182, 212, 0.12); filter: blur(140px); border-radius: 50%; pointer-events: none; z-index: -1;"></div>
    
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=Space+Grotesk:wght@400;500;600;700&display=swap');

    /* Global Layout and Ambient Styling */
    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Outfit', sans-serif !important;
        background-color: #030712 !important;
        background-image: radial-gradient(circle at 15% 15%, rgba(99, 102, 241, 0.08) 0%, transparent 50%),
                          radial-gradient(circle at 85% 85%, rgba(6, 182, 212, 0.08) 0%, transparent 50%) !important;
        background-attachment: fixed !important;
    }
    
    /* Premium Sidebar Configuration */
    [data-testid="stSidebar"] {
        background-color: rgba(8, 10, 18, 0.95) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.05) !important;
        backdrop-filter: blur(24px) !important;
        -webkit-backdrop-filter: blur(24px) !important;
    }
    [data-testid="stSidebar"] * {
        font-family: 'Outfit', sans-serif !important;
    }

    /* Headings styling */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Space Grotesk', sans-serif !important;
        font-weight: 700 !important;
        background: linear-gradient(135deg, #FFFFFF 30%, #C7D2FE 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -0.02em;
    }

    /* Metric Cards Glassmorphism */
    [data-testid="stMetricValue"] {
        font-size: 2.2rem !important;
        font-weight: 700 !important;
        font-family: 'Space Grotesk', sans-serif !important;
        background: linear-gradient(135deg, #FFFFFF 0%, #E2E8F0 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.85rem !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.08em !important;
        color: #94A3B8 !important;
    }
    [data-testid="stMetric"] {
        background: rgba(15, 23, 42, 0.55) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 16px !important;
        padding: 20px 24px !important;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3) !important;
        backdrop-filter: blur(12px) !important;
        -webkit-backdrop-filter: blur(12px) !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }
    [data-testid="stMetric"]:hover {
        transform: translateY(-4px) !important;
        border-color: rgba(99, 102, 241, 0.4) !important;
        box-shadow: 0 12px 40px 0 rgba(99, 102, 241, 0.18) !important;
    }

    /* Expandable Case Container Glassmorphism */
    [data-testid="stExpander"] {
        background: rgba(15, 23, 42, 0.35) !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        border-radius: 12px !important;
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.15) !important;
        backdrop-filter: blur(8px) !important;
        margin-bottom: 16px !important;
        transition: border-color 0.3s ease !important;
    }
    [data-testid="stExpander"]:hover {
        border-color: rgba(99, 102, 241, 0.25) !important;
    }
    
    /* Interactive Navigation Sidebar Buttons */
    [data-testid="stSidebar"] [role="radiogroup"] {
        gap: 10px !important;
    }
    [data-testid="stSidebar"] [role="radiogroup"] label {
        background: rgba(255, 255, 255, 0.015) !important;
        border: 1px solid rgba(255, 255, 255, 0.03) !important;
        padding: 12px 16px !important;
        border-radius: 12px !important;
        color: #94A3B8 !important;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
        margin-bottom: 4px !important;
        cursor: pointer !important;
        display: flex !important;
        align-items: center !important;
        width: 100% !important;
    }
    [data-testid="stSidebar"] [role="radiogroup"] label:hover {
        background: rgba(255, 255, 255, 0.05) !important;
        border-color: rgba(255, 255, 255, 0.08) !important;
        color: #F1F5F9 !important;
        transform: translateX(4px) !important;
    }
    [data-testid="stSidebar"] [role="radiogroup"] [data-checked="true"] label,
    [data-testid="stSidebar"] [role="radiogroup"] label[data-checked="true"],
    [data-testid="stSidebar"] [role="radiogroup"] div[data-checked="true"] label {
        background: linear-gradient(135deg, rgba(99, 102, 241, 0.25) 0%, rgba(6, 182, 212, 0.15) 100%) !important;
        border: 1px solid rgba(99, 102, 241, 0.5) !important;
        color: #FFFFFF !important;
        font-weight: 600 !important;
        box-shadow: 0 4px 20px rgba(99, 102, 241, 0.15) !important;
    }
    
    /* Completely hide the standard circular radio options/dots */
    [data-testid="stSidebar"] [role="radiogroup"] label [data-testid="stRadioHoverHelper"],
    [data-testid="stSidebar"] [role="radiogroup"] label div[role="presentation"],
    [data-testid="stSidebar"] [role="radiogroup"] label span[role="presentation"],
    [data-testid="stSidebar"] [role="radiogroup"] label svg,
    [data-testid="stSidebar"] [role="radiogroup"] label input,
    [data-testid="stSidebar"] [role="radiogroup"] label div:first-child:not([data-testid="stMarkdownContainer"]) {
        display: none !important;
    }

    [data-testid="stSidebar"] [role="radiogroup"] label [data-testid="stMarkdownContainer"] p {
        margin: 0 !important;
        font-size: 1.05rem !important;
        font-weight: inherit !important;
        color: inherit !important;
    }
    
    /* Custom Scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    ::-webkit-scrollbar-track {
        background: rgba(3, 7, 18, 0.5);
    }
    ::-webkit-scrollbar-thumb {
        background: rgba(255, 255, 255, 0.08);
        border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: rgba(99, 102, 241, 0.3);
    }

    /* Buttons styling override */
    button[kind="primary"] {
        background: linear-gradient(135deg, #6366F1 0%, #4F46E5 100%) !important;
        border: none !important;
        border-radius: 10px !important;
        color: #FFFFFF !important;
        font-weight: 600 !important;
        padding: 10px 24px !important;
        box-shadow: 0 4px 15px rgba(99, 102, 241, 0.3) !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }
    button[kind="primary"]:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(99, 102, 241, 0.5) !important;
        background: linear-gradient(135deg, #818CF8 0%, #6366F1 100%) !important;
    }

    /* DataFrame custom borders */
    div[data-testid="stDataFrame"] {
        background: rgba(15, 23, 42, 0.4) !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        border-radius: 12px !important;
        overflow: hidden !important;
        padding: 6px !important;
    }
    
    div[data-testid="stMarkdownContainer"] p, div[data-testid="stMarkdownContainer"] li {
        color: #CBD5E1 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

API_URL = os.getenv("API_URL", "http://localhost:8000")

# ============================================================
# API HELPERS
# ============================================================

def api_get(path: str, params: dict | None = None) -> dict | list | None:
    """Synchronous GET against the API; returns parsed JSON or None on error."""
    try:
        r = httpx.get(f"{API_URL}{path}", params=params, timeout=30)
        r.raise_for_status()
        return r.json()
    except httpx.HTTPStatusError as e:
        st.error(f"API error {e.response.status_code}: {e.response.text}")
    except Exception as e:
        st.error(f"Cannot reach API at {API_URL}: {e}")
    return None


def api_post_file(path: str, file_bytes: bytes, filename: str) -> dict | None:
    """POST a file upload to the API."""
    try:
        r = httpx.post(
            f"{API_URL}{path}",
            files={"file": (filename, file_bytes, "application/x-yaml")},
            timeout=120,
        )
        r.raise_for_status()
        return r.json()
    except httpx.HTTPStatusError as e:
        st.error(f"API error {e.response.status_code}: {e.response.text}")
    except Exception as e:
        st.error(f"Request failed: {e}")
    return None


# ============================================================
# COLOUR HELPERS
# ============================================================

def score_badge(score: float) -> str:
    if score >= 0.8:
        return f"🟢 {score:.3f}"
    if score >= 0.5:
        return f"🟡 {score:.3f}"
    return f"🔴 {score:.3f}"


def score_colour(score: float) -> str:
    if score >= 0.8:
        return "green"
    if score >= 0.5:
        return "orange"
    return "red"


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.title("🔬 EvalForge")
    st.caption("LLM Evaluation Framework")
    st.markdown("---")
    page = st.radio(
        "Navigation",
        ["🏠 Run Overview", "📋 Run Detail", "📈 Score History", "📥 Export", "🏥 Health"],
        label_visibility="collapsed",
    )
    st.markdown("---")
    custom_api = st.text_input("API URL", value=API_URL, key="api_url")
    if custom_api:
        API_URL = custom_api

# ============================================================
# PAGE 1 — RUN OVERVIEW
# ============================================================

if page == "🏠 Run Overview":
    st.title("🏠 Run Overview")

    # Upload + Run
    with st.expander("▶  Run a new test suite", expanded=False):
        uploaded = st.file_uploader("Upload YAML suite", type=["yaml", "yml"])
        if uploaded and st.button("🚀 Run Suite", type="primary"):
            with st.spinner("Running suite — this may take a minute…"):
                result = api_post_file("/suites/run", uploaded.read(), uploaded.name)
            if result:
                st.success(f"✅ Run complete: **{result['run_id']}** — avg score **{result['avg_score']:.3f}**")
                if result.get("is_regression"):
                    st.warning("⚠️ Regression detected on this run!")
                st.rerun()

    st.markdown("---")

    data = api_get("/runs", {"limit": 200})
    runs = data.get("runs", []) if data else []

    if not runs:
        # Stunning glassmorphic onboarding screen
        st.markdown(
            """
            <div style="background: rgba(17, 24, 39, 0.4); border: 1px solid rgba(255, 255, 255, 0.08); padding: 32px; border-radius: 20px; box-shadow: 0 10px 40px rgba(0, 0, 0, 0.4); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); margin-bottom: 24px;">
                <h2 style="margin-top: 0; background: linear-gradient(135deg, #A5B4FC 0%, #818CF8 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">Welcome to EvalForge 🔬</h2>
                <p style="color: #94A3B8; font-size: 1.1rem; line-height: 1.6;">
                    EvalForge is a lightweight, open-source prompt engineering and evaluation framework. 
                    Continuously test prompt quality, track output semantic similarity, calculate LLM judge metrics, and discover regression drift instantly across models.
                </p>
                <hr style="border: 0; border-top: 1px solid rgba(255, 255, 255, 0.08); margin: 24px 0;">
                <h3 style="font-size: 1.2rem; color: #E2E8F0; margin-bottom: 16px;">Quick Start Blueprint</h3>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px;">
                    <div style="background: rgba(255,255,255,0.015); border: 1px solid rgba(255,255,255,0.03); padding: 20px; border-radius: 12px;">
                        <span style="font-size: 2rem;">📄</span>
                        <h4 style="margin: 12px 0 6px 0; color: #FFFFFF; font-size: 1rem;">1. Define Cases</h4>
                        <p style="margin: 0; color: #94A3B8; font-size: 0.9rem; line-height: 1.4;">Write inputs, expected answers, and target models in a simple YAML configuration.</p>
                    </div>
                    <div style="background: rgba(255,255,255,0.015); border: 1px solid rgba(255,255,255,0.03); padding: 20px; border-radius: 12px;">
                        <span style="font-size: 2rem;">🚀</span>
                        <h4 style="margin: 12px 0 6px 0; color: #FFFFFF; font-size: 1rem;">2. Run Evaluation</h4>
                        <p style="margin: 0; color: #94A3B8; font-size: 0.9rem; line-height: 1.4;">Upload your suite using the drawer above, or trigger runs via standard API POST requests.</p>
                    </div>
                    <div style="background: rgba(255,255,255,0.015); border: 1px solid rgba(255,255,255,0.03); padding: 20px; border-radius: 12px;">
                        <span style="font-size: 2rem;">📈</span>
                        <h4 style="margin: 12px 0 6px 0; color: #FFFFFF; font-size: 1rem;">3. Analyze Drift</h4>
                        <p style="margin: 0; color: #94A3B8; font-size: 0.9rem; line-height: 1.4;">Track scores over time, review exact latency, and pinpoint regression anomalies immediately.</p>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown("<h3 style='font-weight: 600; font-size: 1.25rem; background: linear-gradient(135deg, #FFFFFF 30%, #C7D2FE 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>Ready to see it in action?</h3>", unsafe_allow_html=True)
        st.write("Click below to instantly run our customer support benchmark suite using your OpenAI credentials!")
        
        if st.button("🚀 Run Demo Test Suite", type="primary"):
            # Load example_suite.yaml from test_suites/
            try:
                example_path = "test_suites/example_suite.yaml"
                with open(example_path, "rb") as f:
                    file_bytes = f.read()
                with st.spinner("Executing 10 evaluation test cases across scorers..."):
                    result = api_post_file("/suites/run", file_bytes, "example_suite.yaml")
                if result:
                    st.success(f"✅ Demo completed: **{result['run_id']}** — average performance score **{result['avg_score']:.3f}**")
                    st.rerun()
            except Exception as e:
                st.error(f"Failed to execute demo suite: {e}")
        st.stop()

    # Suite filter
    suites = sorted({r["suite_name"] for r in runs})
    selected_suite = st.selectbox("Filter by suite", ["All"] + suites)
    filtered = runs if selected_suite == "All" else [r for r in runs if r["suite_name"] == selected_suite]

    # KPI row
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Runs", len(filtered))
    avg = sum(r["avg_score"] for r in filtered) / len(filtered) if filtered else 0
    c2.metric("Mean Score", f"{avg:.3f}")
    c3.metric("Pass Rate", f"{sum(r['pass_count'] for r in filtered)}/{sum(r['total_cases'] for r in filtered)}")
    regressions = sum(1 for r in filtered if r["is_regression"])
    c4.metric("Regressions", regressions, delta=f"-{regressions}" if regressions else "none", delta_color="inverse")

    st.markdown("---")
    st.subheader("All Runs")

    rows = []
    for r in filtered:
        ts = datetime.fromisoformat(r["timestamp"].replace("Z", "+00:00"))
        rows.append({
            "Run ID": r["run_id"],
            "Suite": r["suite_name"],
            "Model": r["model"],
            "Timestamp": ts.strftime("%Y-%m-%d %H:%M UTC"),
            "Cases": r["total_cases"],
            "Pass": r["pass_count"],
            "Avg Score": f"{r['avg_score']:.3f}",
            "Status": "🔴 Regression" if r["is_regression"] else "✅ OK",
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)


# ============================================================
# PAGE 2 — RUN DETAIL
# ============================================================

elif page == "📋 Run Detail":
    st.title("📋 Run Detail")

    data = api_get("/runs", {"limit": 200})
    if not data or not data.get("runs"):
        st.info("No runs found.")
        st.stop()

    run_options = {r["run_id"]: f"{r['run_id']}  [{r['suite_name']} · {r['avg_score']:.3f}]"
                   for r in data["runs"]}
    selected_id = st.selectbox("Select Run", list(run_options.keys()),
                               format_func=lambda k: run_options[k])

    detail = api_get(f"/runs/{selected_id}")
    if not detail:
        st.stop()

    # Header metrics
    total = detail["total_cases"]
    passes = detail["pass_count"]
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Cases", total)
    c2.metric("Passed", passes)
    c3.metric("Pass Rate", f"{passes/total*100:.1f}%" if total else "—")
    c4.metric("Avg Score", f"{detail['avg_score']:.3f}")
    reg_label = "🔴 Regression" if detail["is_regression"] else "✅ OK"
    c5.metric("Status", reg_label)

    st.caption(f"Model: **{detail['model']}** · Suite: **{detail['suite_name']}**")
    st.markdown("---")

    # Per-scorer summary chart
    results = detail.get("results", [])
    if results:
        scorer_avgs: dict[str, list[float]] = {}
        for cr in results:
            for sc, val in cr.get("scores", {}).items():
                scorer_avgs.setdefault(sc, []).append(val)

        if scorer_avgs:
            fig = go.Figure()
            # TAILORED HIGH-CONTRAST PALETTE FOR SCORERS
            colors = {
                "exact_match": "#10B981",         # Emerald
                "semantic_similarity": "#06B6D4",   # Cyan
                "llm_judge": "#6366F1",             # Indigo
            }
            
            for sc, vals in scorer_avgs.items():
                col = colors.get(sc, "#8B5CF6")
                avg_val = sum(vals)/len(vals)
                fig.add_trace(go.Bar(
                    name=sc.replace("_", " ").title(),
                    x=[sc.replace("_", " ").title()],
                    y=[avg_val],
                    marker=dict(
                        color=col,
                        line=dict(color=col, width=1),
                        opacity=0.85
                    ),
                    hovertemplate="Scorer: %{x}<br>Avg Score: %{y:.3f}<extra></extra>"
                ))
                
            fig.update_layout(
                title=dict(
                    text="Average Score per Scorer",
                    font=dict(family="Space Grotesk", size=16, color="#F8FAFC")
                ),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                yaxis=dict(
                    range=[0, 1.05],
                    gridcolor="rgba(255,255,255,0.06)",
                    tickfont=dict(color="#94A3B8"),
                    title=dict(text="Average Score", font=dict(color="#94A3B8"))
                ),
                xaxis=dict(
                    tickfont=dict(color="#94A3B8")
                ),
                height=300,
                margin=dict(t=50, b=30, l=40, r=20),
                showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True)

    # Case table
    st.subheader("Case Results")
    table_rows = []
    for cr in results:
        avg = cr.get("avg_score", 0)
        table_rows.append({
            "Case ID": cr["case_id"],
            "Score": score_badge(avg),
            "Latency": f"{cr.get('latency_ms', 0)} ms",
            "Input (preview)": cr["input"][:60] + ("…" if len(cr["input"]) > 60 else ""),
        })
    st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)

    # Expandable detail per case
    st.subheader("Detailed Breakdown")
    for cr in results:
        avg = cr.get("avg_score", 0)
        with st.expander(f"{score_badge(avg)}  {cr['case_id']}", expanded=False):
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("**Input**")
                st.text(cr["input"])
                st.markdown("**Expected**")
                st.text(cr["expected"])
            with col_b:
                st.markdown("**Actual**")
                st.text(cr["actual"])
                st.markdown(f"**Latency:** {cr.get('latency_ms', '—')} ms")

            st.markdown("**Scorer Results**")
            scorer_cols = st.columns(len(cr.get("details", [])) or 1)
            for idx, sd in enumerate(cr.get("details", [])):
                with scorer_cols[idx]:
                    st.metric(sd["scorer"], score_badge(sd["score"]))
                    if sd.get("reason"):
                        st.caption(sd["reason"])


# ============================================================
# PAGE 3 — SCORE HISTORY & DRIFT
# ============================================================

elif page == "📈 Score History":
    st.title("📈 Score History & Drift")

    data = api_get("/runs", {"limit": 200})
    if not data or not data.get("runs"):
        st.info("No runs found.")
        st.stop()

    suites = sorted({r["suite_name"] for r in data["runs"]})
    suite_name = st.selectbox("Select Suite", suites)

    history_data = api_get(f"/suites/{suite_name}/history")
    if not history_data:
        st.stop()

    history = history_data.get("history", [])
    if not history:
        st.info(f"No history for suite **{suite_name}** yet.")
        st.stop()

    df = pd.DataFrame([
        {
            "timestamp": datetime.fromisoformat(h["timestamp"].replace("Z", "+00:00")),
            "run_id": h["run_id"],
            "avg_score": h["avg_score"],
            "exact_match": (h.get("scorer_breakdown") or {}).get("exact_match"),
            "semantic_similarity": (h.get("scorer_breakdown") or {}).get("semantic_similarity"),
            "llm_judge": (h.get("scorer_breakdown") or {}).get("llm_judge"),
        }
        for h in history
    ]).sort_values("timestamp")

    # KPIs
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Runs", len(df))
    latest = df["avg_score"].iloc[-1]
    first = df["avg_score"].iloc[0]
    c2.metric("Latest Score", f"{latest:.3f}", delta=f"{latest - first:+.3f}")

    last5 = df["avg_score"].tail(5)
    drift = float(last5.std()) if len(last5) > 1 else 0.0
    c3.metric("Prompt Drift Index", f"{drift:.4f}", help="Std dev of last 5 runs — lower is more stable")

    regressions = sum(
        1 for i in range(1, len(df))
        if df["avg_score"].iloc[i] < df["avg_score"].iloc[i - 1] - 0.05
    )
    c4.metric("Regressions", regressions)

    st.markdown("---")

    # Line chart
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df["timestamp"], y=df["avg_score"],
        mode="lines+markers", name="Avg Score",
        line=dict(color="#6366F1", width=3.5),
        marker=dict(size=8, color="#6366F1", line=dict(color="#FFFFFF", width=1.5)),
        hovertemplate="Avg Score: %{y:.3f}<extra></extra>"
    ))

    colors = {
        "exact_match": ("#10B981", "dash"),           # Emerald
        "semantic_similarity": ("#06B6D4", "dot"),     # Cyan
        "llm_judge": ("#8B5CF6", "dashdot"),           # Purple
    }

    for col, (colour, dash) in colors.items():
        series = df[col].dropna()
        if not series.empty:
            fig.add_trace(go.Scatter(
                x=df.loc[series.index, "timestamp"], y=series,
                mode="lines+markers", name=col.replace("_", " ").title(),
                line=dict(color=colour, dash=dash, width=2),
                marker=dict(size=5, color=colour),
                hovertemplate=f"{col.replace('_', ' ').title()}: %{{y:.3f}}<extra></extra>"
            ))

    # Highlight regression points
    for i in range(1, len(df)):
        if df["avg_score"].iloc[i] < df["avg_score"].iloc[i - 1] - 0.05:
            fig.add_vline(
                x=df["timestamp"].iloc[i].timestamp() * 1000,
                line_color="#EF4444", line_dash="dash", opacity=0.7,
                annotation_text="⚠️ regression",
                annotation_position="top left",
                annotation_font=dict(color="#EF4444", size=10)
            )

    fig.update_layout(
        title=dict(
            text=f"Score History & Drift — {suite_name}",
            font=dict(family="Space Grotesk", size=18, color="#F8FAFC")
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(
            gridcolor="rgba(255,255,255,0.06)",
            tickfont=dict(color="#94A3B8"),
            title=dict(text="Run Time", font=dict(color="#94A3B8"))
        ),
        yaxis=dict(
            gridcolor="rgba(255,255,255,0.06)",
            tickfont=dict(color="#94A3B8"),
            title=dict(text="Score", font=dict(color="#94A3B8")),
            range=[0, 1.05]
        ),
        hovermode="x unified",
        height=420,
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
            font=dict(color="#CBD5E1")
        ),
        margin=dict(t=60, b=40, l=40, r=20)
    )
    st.plotly_chart(fig, use_container_width=True)

    # History table
    st.subheader("Run History")
    display = df[["timestamp", "run_id", "avg_score"]].copy()
    display["avg_score"] = display["avg_score"].apply(lambda x: f"{x:.4f}")
    display["timestamp"] = display["timestamp"].dt.strftime("%Y-%m-%d %H:%M UTC")
    display.columns = ["Timestamp", "Run ID", "Avg Score"]
    st.dataframe(display, use_container_width=True, hide_index=True)


# ============================================================
# PAGE 4 — EXPORT
# ============================================================

elif page == "📥 Export":
    st.title("📥 Export Results")

    data = api_get("/runs", {"limit": 200})
    if not data or not data.get("runs"):
        st.info("No runs found.")
        st.stop()

    run_options = {r["run_id"]: f"{r['run_id']}  [{r['suite_name']} · {r['avg_score']:.3f}]"
                   for r in data["runs"]}
    selected_id = st.selectbox("Select Run", list(run_options.keys()),
                               format_func=lambda k: run_options[k])

    fmt = st.radio("Format", ["CSV", "JSON"], horizontal=True)
    fmt_param = fmt.lower()

    try:
        r = httpx.get(f"{API_URL}/runs/{selected_id}/export",
                      params={"format": fmt_param}, timeout=30)
        r.raise_for_status()

        mime = "text/csv" if fmt_param == "csv" else "application/json"
        st.download_button(
            label=f"⬇  Download {fmt}",
            data=r.content,
            file_name=f"{selected_id}.{fmt_param}",
            mime=mime,
            type="primary",
        )
        st.success(f"Ready to download **{selected_id}.{fmt_param}**")

        # Preview
        if fmt_param == "csv":
            import io
            preview_df = pd.read_csv(io.BytesIO(r.content))
            st.dataframe(preview_df.head(20), use_container_width=True, hide_index=True)
        else:
            payload = r.json()
            st.json(payload, expanded=False)

    except Exception as e:
        st.error(f"Export failed: {e}")


# ============================================================
# PAGE 5 — HEALTH
# ============================================================

elif page == "🏥 Health":
    st.title("🏥 API Health")

    health = api_get("/health")

    col1, col2 = st.columns(2)
    with col1:
        if health and health.get("status") == "ok":
            st.success(f"✅ API is running  (v{health.get('version', '?')})")
            st.success(f"✅ Database: {health.get('database', 'unknown')}")
        else:
            st.error("❌ API is unreachable")

    with col2:
        st.subheader("Response")
        st.json(health or {"status": "unreachable"})

    st.markdown("---")
    st.subheader("Endpoint Reference")

    endpoints = {
        "GET  /health":                          "Health check",
        "POST /suites/run":                      "Upload YAML and run suite",
        "GET  /suites/{suite_name}/history":     "Score history for regression/drift",
        "GET  /runs":                            "List all runs (supports ?suite= filter)",
        "GET  /runs/{run_id}":                   "Full results for one run",
        "GET  /runs/{run_id}/export?format=csv": "Download results as CSV or JSON",
    }
    for ep, desc in endpoints.items():
        st.markdown(f"`{ep}` — {desc}")

    st.markdown("---")
    st.caption(f"API URL: **{API_URL}** · [OpenAPI Docs]({API_URL}/docs)")
