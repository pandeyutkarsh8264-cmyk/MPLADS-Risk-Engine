"""MPLADS Risk Intelligence & Investigation Engine — Command Center.

SIH26102 Implementation:
Government of India MoSPI 18th Lok Sabha Screening & Multimodal Evidence Fusion.

Provides:
- Executive / Portfolio KPIs on all 106,261 real works
- Ranked Risk Queue with availability-normalized risk scores
- Deep-Dive Work Investigation View with structured evidence objects
- Exact 4-Engine Breakdown (Peer Benchmarking, Statistical Outliers, Mismatch, Duplicate)
- Concrete next-step investigation actions without fraud/guilt claims
- Evidence traceability and source provenance
"""

import sys
from pathlib import Path
from typing import Dict, Any, Optional, List

import streamlit as st
import pandas as pd
import numpy as np

# Ensure root directory is in sys.path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.ui_helpers import (
    CUSTOM_CSS,
    get_risk_badge_html,
    get_confidence_badge_html,
    format_inr,
    format_display_date,
    clean_html,
    get_metric_card_html,
    render_executive_console_html,
    render_risk_concentration_html,
    render_evidence_governance_html,
    render_case_dossier_header_html,
    render_milestone_timeline_html,
    render_math_breakdown_html,
    synthesize_plain_language_narrative,
    render_risk_drivers_html,
    render_duplicate_comparison_html,
    RISK_COLORS
)
from src.peer_benchmark import PeerBenchmarkEngine
from src.statistical_outliers import StatisticalOutlierEngine
from src.mismatch import FinancialExecutionMismatchEngine
from src.duplicate_overlap import DuplicateOverlapEngine
from src.fusion import RiskFusionEngine, WorkRisk

# Page Configuration
st.set_page_config(
    page_title="MPPrisma — Risk Intelligence & Investigation Platform",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inject dark professional stylesheet
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# =============================================================================
# DATA AND MODEL CACHING
# =============================================================================

@st.cache_data(show_spinner=False)
def load_scored_portfolio() -> pd.DataFrame:
    """Loads the pre-scored 18th Lok Sabha portfolio summary."""
    p_path = ROOT_DIR / "data" / "processed" / "scored_work_summary.parquet"
    if p_path.exists():
        df = pd.read_parquet(p_path)
    else:
        # Fallback to sample outputs
        sample_path = ROOT_DIR / "artifacts" / "demo_outputs" / "sample_final_work_risk_outputs.json"
        import json
        with open(sample_path, "r", encoding="utf-8") as f:
            samples = json.load(f)
        rows = []
        for s in samples:
            meta = s.get("work_metadata", {})
            rows.append({
                "work_recommendation_dtl_id": meta.get("work_recommendation_dtl_id"),
                "work_id": s.get("work_id"),
                "mp_name": meta.get("mp_name"),
                "state": meta.get("state"),
                "constituency": meta.get("constituency"),
                "district": meta.get("district"),
                "category": meta.get("category"),
                "work_description": meta.get("work_description"),
                "work_stage": meta.get("work_stage"),
                "year": "2024-2025",
                "amount_recommended": meta.get("amount_recommended"),
                "amount_sanctioned": meta.get("amount_sanctioned"),
                "amount_completed": meta.get("amount_completed"),
                "total_disbursed_amount": meta.get("total_disbursed_amount"),
                "peer_score": s.get("module_scores", {}).get("peer_benchmarking"),
                "stat_score": s.get("module_scores", {}).get("statistical_outliers"),
                "mismatch_score": s.get("module_scores", {}).get("financial_execution_mismatch"),
                "duplicate_score": s.get("module_scores", {}).get("duplicate_overlap"),
                "risk_score": s.get("risk_score"),
                "risk_band": s.get("risk_band"),
                "available_weight_pct": s.get("evidence_coverage", {}).get("available_weight_pct", 100.0),
                "observed_vs_proxy": s.get("evidence_coverage", {}).get("observed_vs_proxy", "fully_observed"),
                "has_completion_evidence": meta.get("is_completed", False),
                "has_expenditure_evidence": meta.get("total_disbursed_amount") is not None,
                "investigation_required": s.get("risk_band") in ("CRITICAL", "HIGH")
            })
        df = pd.DataFrame(rows)
    return df


@st.cache_data(show_spinner=False)
def load_canonical_master_df() -> pd.DataFrame:
    """Loads the canonical joined master table for deep investigation."""
    p_path = ROOT_DIR / "data" / "processed" / "canonical_work_master.parquet"
    if p_path.exists():
        return pd.read_parquet(p_path)
    return pd.DataFrame()


@st.cache_resource(show_spinner=False)
def load_fitted_engines():
    """Initializes and fits all 4 core risk engines on the master corpus."""
    master_df = load_canonical_master_df()
    if master_df.empty:
        return None, None, None, None, RiskFusionEngine()
    master_records = master_df.to_dict("records")
    
    peer_eng = PeerBenchmarkEngine(min_cohort_size=10).fit(master_records)
    stat_eng = StatisticalOutlierEngine().fit(master_records)
    mismatch_eng = FinancialExecutionMismatchEngine().fit_peer_durations(master_records)
    dup_eng = DuplicateOverlapEngine().build_index(master_records)
    fusion_eng = RiskFusionEngine()
    
    return peer_eng, stat_eng, mismatch_eng, dup_eng, fusion_eng


# Load portfolio data
df_portfolio = load_scored_portfolio()


# =============================================================================
# TOP MASTHEAD
# =============================================================================

st.markdown("""
<div class="masthead-container">
    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
        <div>
            <div style="font-size: 0.85rem; font-weight: 700; color: #58a6ff; letter-spacing: 1.5px; text-transform: uppercase;">
                MoSPI • 18th Lok Sabha Intelligence System
            </div>
            <h1 style="font-size: 1.95rem; margin: 4px 0 2px 0; color: #f0f6fc; letter-spacing: -0.5px;">
                MPPrisma
            </h1>
            <div style="font-size: 1.05rem; font-weight: 500; color: #79c0ff; margin-bottom: 4px;">
                Risk Intelligence & Investigation Platform
            </div>
            <div style="font-size: 0.82rem; color: #8b949e;">
                SIH26102 Authoritative Screening • Multi-Engine Evidence Fusion • 106,261 Validated Projects
            </div>
        </div>
        <div style="text-align: right; margin-top: 8px;">
            <span style="background: rgba(31, 111, 235, 0.15); color: #58a6ff; border: 1px solid #1f6feb; padding: 4px 10px; border-radius: 6px; font-size: 0.8rem; font-weight: 600;">
                PROVENANCE: GOI MoSPI API
            </span>
            <div style="font-size: 0.75rem; color: #8b949e; margin-top: 4px;">
                Exact Join Key: <code>WORK_RECOMMENDATION_DTL_ID</code>
            </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


# =============================================================================
# SIDEBAR FILTERS
# =============================================================================

st.sidebar.markdown("### 🔍 Portfolio Filters")

# State filter
all_states = sorted([s for s in df_portfolio["state"].dropna().unique() if s != "Unknown State"])
state_opts = ["All States"] + all_states
sel_state = st.sidebar.selectbox("State", state_opts, index=0)

# Filter dataframe based on state
if sel_state != "All States":
    df_filtered = df_portfolio[df_portfolio["state"] == sel_state]
else:
    df_filtered = df_portfolio

# Constituency / District filter
available_constituencies = sorted([c for c in df_filtered["constituency"].dropna().unique() if c != "Unknown Constituency"])
constituency_opts = ["All Constituencies"] + available_constituencies
sel_constituency = st.sidebar.selectbox("Constituency", constituency_opts, index=0)

if sel_constituency != "All Constituencies":
    df_filtered = df_filtered[df_filtered["constituency"] == sel_constituency]

# Category filter
available_categories = sorted([c for c in df_filtered["category"].dropna().unique() if c])
category_opts = ["All Categories"] + available_categories
sel_category = st.sidebar.selectbox("Work Category", category_opts, index=0)

if sel_category != "All Categories":
    df_filtered = df_filtered[df_filtered["category"] == sel_category]

# Work Stage filter
available_stages = sorted([s for s in df_filtered["work_stage"].dropna().unique() if s])
stage_opts = ["All Stages"] + available_stages
sel_stage = st.sidebar.selectbox("Work Stage", stage_opts, index=0)

if sel_stage != "All Stages":
    df_filtered = df_filtered[df_filtered["work_stage"] == sel_stage]

# Risk Band filter
band_opts = ["All Bands", "CRITICAL (80-100)", "HIGH (60-79)", "MEDIUM (30-59)", "LOW (0-29)"]
sel_band_str = st.sidebar.selectbox("Risk Band", band_opts, index=0)

if sel_band_str.startswith("CRITICAL"):
    df_filtered = df_filtered[df_filtered["risk_band"] == "CRITICAL"]
elif sel_band_str.startswith("HIGH"):
    df_filtered = df_filtered[df_filtered["risk_band"] == "HIGH"]
elif sel_band_str.startswith("MEDIUM"):
    df_filtered = df_filtered[df_filtered["risk_band"] == "MEDIUM"]
elif sel_band_str.startswith("LOW"):
    df_filtered = df_filtered[df_filtered["risk_band"] == "LOW"]

# Search filter
search_term = st.sidebar.text_input("Search (Work ID, DTL ID, MP Name)", "").strip().lower()
if search_term:
    df_filtered = df_filtered[
        df_filtered["work_id"].str.lower().str.contains(search_term, na=False) |
        df_filtered["work_recommendation_dtl_id"].astype(str).str.contains(search_term, na=False) |
        df_filtered["mp_name"].str.lower().str.contains(search_term, na=False) |
        df_filtered["work_description"].str.lower().str.contains(search_term, na=False)
    ]

# Display filter count badge
n_filtered = len(df_filtered)
n_total = len(df_portfolio)
pct_filt = (n_filtered / n_total * 100.0) if n_total > 0 else 0.0

st.sidebar.markdown(f"""
<div style="background-color: #21262d; border: 1px solid #30363d; border-radius: 6px; padding: 10px; margin-top: 15px;">
    <div style="font-size: 0.75rem; color: #8b949e; text-transform: uppercase; font-weight: 600;">Selection Scope</div>
    <div style="font-size: 1.1rem; font-weight: 700; color: #f0f6fc;">{n_filtered:,} <span style="font-size: 0.8rem; color: #8b949e;">/ {n_total:,} works</span></div>
    <div style="font-size: 0.75rem; color: #58a6ff;">({pct_filt:.1f}% of total portfolio)</div>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("---")
st.sidebar.markdown("""
<div style="font-size: 0.75rem; color: #8b949e; line-height: 1.4;">
    <strong>Investigative Safeguard:</strong><br>
    Scores reflect statistical anomaly severity and milestone deviation. Does not imply confirmed fraud or guilt.
</div>
""", unsafe_allow_html=True)


# =============================================================================
# MAIN NAVIGATION TABS (A through F)
# =============================================================================

tab_cmd, tab_queue, tab_investigate, tab_compare, tab_dataset, tab_meta = st.tabs([
    "🏛️ Command Center",
    "📋 Risk Queue",
    "🔍 Investigation",
    "⚖️ Compare / Overlap",
    "📁 Analyze Your Dataset",
    "ℹ️ Methodology & Provenance"
])


# =============================================================================
# A. COMMAND CENTER
# =============================================================================

with tab_cmd:
    # Calculate actual computed portfolio metrics
    crit_count = int((df_filtered["risk_band"] == "CRITICAL").sum())
    high_count = int((df_filtered["risk_band"] == "HIGH").sum())
    med_count = int((df_filtered["risk_band"] == "MEDIUM").sum())
    low_count = int((df_filtered["risk_band"] == "LOW").sum())
    total_screened = len(df_filtered)
    scored_count = int(df_filtered["risk_score"].notna().sum())
    
    avg_score = df_filtered["risk_score"].dropna().mean() if scored_count > 0 else 0.0
    avg_coverage = df_filtered["available_weight_pct"].dropna().mean() if total_screened > 0 else 0.0
    priority_count = crit_count + high_count

    # 1. PORTFOLIO STATE: Sovereign Executive Console Banner (Unified Intelligence, not floating cards)
    st.markdown(render_executive_console_html(
        total_screened=total_screened,
        scored_count=scored_count,
        priority_count=priority_count,
        avg_score=avg_score,
        avg_coverage=avg_coverage,
        low_count=low_count,
        crit_count=crit_count,
        high_count=high_count
    ), unsafe_allow_html=True)

    # 2. WHAT STANDS OUT: Dual Analytical Panels (Risk Concentration vs Evidence Governance)
    col_anal_l, col_anal_r = st.columns([1, 1])
    with col_anal_l:
        st.markdown(render_risk_concentration_html(
            low_c=low_count,
            med_c=med_count,
            high_c=high_count,
            crit_c=crit_count,
            total_c=total_screened
        ), unsafe_allow_html=True)

    with col_anal_r:
        st.markdown(render_evidence_governance_html(), unsafe_allow_html=True)

    # 3. WHERE TO LOOK NEXT: Executive Priority Review Ledger
    st.markdown("<div style='margin-top: 24px;'></div>", unsafe_allow_html=True)
    st.markdown("#### 🚨 Priority Action Ledger — Urgent Administrative Review")
    st.markdown("Actionable previews of highest-variance projects flagged for acute cost divergence, milestone delay, or candidate overlap:")

    top_critical = df_filtered.sort_values(by="risk_score", ascending=False).head(4)
    if not top_critical.empty:
        pri_cols = st.columns(len(top_critical))
        for idx, (_, row) in enumerate(top_critical.iterrows()):
            with pri_cols[idx]:
                r_score = row.get("risk_score")
                r_band = row.get("risk_band")
                raw_wid = row.get("work_id")
                raw_dtl = row.get("work_recommendation_dtl_id")
                dtl_disp = int(float(raw_dtl)) if pd.notna(raw_dtl) and str(raw_dtl) not in ("nan", "None", "") else 0
                w_id = str(raw_wid) if pd.notna(raw_wid) and str(raw_wid) not in ("nan", "None", "") else f"DTL_{dtl_disp}"
                desc = row.get("work_description") or ""
                rec_amt = format_inr(row.get("amount_recommended"))
                loc = f"{row.get('constituency')}, {row.get('state')}"
                cov_val = row.get("available_weight_pct")
                cov_disp = f"{cov_val:.0f}%" if pd.notna(cov_val) else "—"

                st.markdown(f"""
                <div style="background-color: #111827; border: 1px solid #1e293b; border-radius: 6px; padding: 14px; height: 210px; display: flex; flex-direction: column; justify-content: space-between;">
                    <div>
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                            <span style="font-size: 0.72rem; color: #38bdf8; font-weight: 700; text-transform: uppercase;">CASE #{idx+1}</span>
                            {get_risk_badge_html(r_band, r_score)}
                        </div>
                        <div style="font-size: 0.88rem; font-weight: 700; color: #f8fafc; margin-bottom: 2px;">{w_id}</div>
                        <div style="font-size: 0.75rem; color: #94a3b8; margin-bottom: 6px;">📍 {loc}</div>
                        <div style="font-size: 0.78rem; color: #cbd5e1; line-height: 1.35; overflow: hidden; max-height: 44px;">
                            {desc[:85]}...
                        </div>
                    </div>
                    <div style="border-top: 1px solid #1e293b; padding-top: 6px; display: flex; justify-content: space-between; font-size: 0.78rem; color: #94a3b8;">
                        <span>Sanction: <strong style="color: #f8fafc;">{rec_amt}</strong></span>
                        <span>Coverage: <strong style="color: #38bdf8;">{cov_disp}</strong></span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                if st.button(f"🔍 Open Case File #{idx+1}", key=f"cmd_inv_{dtl_disp}"):
                    st.session_state["selected_dtl_id"] = dtl_disp
                    st.success(f"Selected DTL {dtl_disp}. Navigate to '🔍 Investigation' tab to view dossier.")


# =============================================================================
# B. RISK QUEUE
# =============================================================================

with tab_queue:
    st.markdown("### 📋 Ranked Portfolio Risk Queue")
    st.markdown("Sortable register of evaluated projects prioritized by composite risk score.")

    col_sort_l, col_sort_m, col_sort_r = st.columns([2, 2, 2])
    with col_sort_l:
        top_n = st.selectbox("Display Count", [50, 100, 250, 500, "All Matching"], index=0)
    with col_sort_m:
        sort_order = st.selectbox("Sort Order", ["Risk Score (Highest First)", "Recommended Amount (Highest First)", "Evidence Coverage (Lowest First)"])
    with col_sort_r:
        st.markdown("<div style='margin-top: 24px;'></div>", unsafe_allow_html=True)
        show_engine_scores = st.checkbox("Show individual engine columns", value=False)

    # Apply sorting with safe NaN handling
    df_sorted = df_filtered.copy()
    if "Risk Score" in sort_order:
        df_sorted = df_sorted.sort_values(by="risk_score", ascending=False, na_position="last")
    elif "Recommended Amount" in sort_order:
        df_sorted = df_sorted.sort_values(by="amount_recommended", ascending=False, na_position="last")
    elif "Coverage" in sort_order:
        df_sorted = df_sorted.sort_values(by="available_weight_pct", ascending=True, na_position="first")

    if top_n != "All Matching":
        df_display = df_sorted.head(int(top_n))
    else:
        df_display = df_sorted

    n_rows = len(df_display)

    # High-performance column construction (vectorized/list comprehensions)
    ranks = np.arange(1, n_rows + 1)
    raw_wids = df_display["work_id"].fillna("").astype(str).tolist()
    raw_dtls = df_display["work_recommendation_dtl_id"].tolist()

    dtl_clean_list = []
    wid_clean_list = []
    work_id_col = []

    for wid, dtl in zip(raw_wids, raw_dtls):
        if pd.notna(dtl) and str(dtl) not in ("nan", "None", "", "<NA>"):
            d_str = str(int(float(dtl)))
            dtl_num = int(float(dtl))
        else:
            d_str = "—"
            dtl_num = None
        w = wid if wid and wid not in ("nan", "None") else f"DTL_{d_str}"
        dtl_clean_list.append(dtl_num)
        wid_clean_list.append(w)
        work_id_col.append(f"{w} ({d_str})")

    state_col = df_display["state"].fillna("—").astype(str).tolist()
    cat_col = df_display["category"].fillna("—").astype(str).tolist()
    amt_col = [format_inr(a) for a in df_display["amount_recommended"].tolist()]
    score_col = [f"{s:.2f}" if pd.notna(s) else "—" for s in df_display["risk_score"].tolist()]
    band_col = df_display["risk_band"].fillna("UNAVAILABLE").astype(str).tolist()
    cov_col = [f"{c:.0f}%" if pd.notna(c) else "—" for c in df_display["available_weight_pct"].tolist()]

    # Exact 8 default columns
    data_dict = {
        "Rank": ranks,
        "Work / DTL ID": work_id_col,
        "State": state_col,
        "Category": cat_col,
        "Amount": amt_col,
        "Risk Score": score_col,
        "Risk Band": band_col,
        "Coverage": cov_col,
    }

    if show_engine_scores:
        data_dict["Peer (30%)"] = [f"{s:.1f}" if pd.notna(s) else "—" for s in df_display["peer_score"].tolist()]
        data_dict["Stat (25%)"] = [f"{s:.1f}" if pd.notna(s) else "—" for s in df_display["stat_score"].tolist()]
        data_dict["Mismatch (30%)"] = [f"{s:.1f}" if pd.notna(s) else "—" for s in df_display["mismatch_score"].tolist()]
        data_dict["Duplicate (15%)"] = [f"{s:.1f}" if pd.notna(s) else "—" for s in df_display["duplicate_score"].tolist()]

    df_view = pd.DataFrame(data_dict)
    st.dataframe(df_view, use_container_width=True, hide_index=True, height=460)

    # Quick selector to send work directly to Investigation View
    st.markdown("#### 🔎 Select a Project for Investigation Deep Dive")
    if n_rows > 0:
        sel_limit = min(100, n_rows)
        opts = [f"#{ranks[i]} - {wid_clean_list[i]} (Score: {score_col[i]}, Band: {band_col[i]}) | {state_col[i]}" for i in range(sel_limit)]
        sel_idx = st.selectbox(f"Choose work from top {sel_limit} in current queue", range(len(opts)), format_func=lambda i: opts[i], index=0)
        sel_dtl_id = dtl_clean_list[sel_idx]
        
        if st.button("🚀 Open in Work Investigation View"):
            if sel_dtl_id is not None:
                st.session_state["selected_dtl_id"] = int(sel_dtl_id)
                st.success(f"Selected Work DTL ID: {int(sel_dtl_id)}. Switch to '🔍 Investigation' tab to view dossier.")
            else:
                st.warning("Selected record does not have a valid DTL ID.")


# =============================================================================
# C. INVESTIGATION (HERO EXPERIENCE — CASE DOSSIER)
# =============================================================================

with tab_investigate:
    st.markdown("### 🔍 Dedicated Project Investigation Deep Dive")
    st.markdown("Comprehensive evidence inspection, multi-engine breakdown, and objective field/desk review actions.")

    # Determine which work to investigate
    default_dtl = st.session_state.get("selected_dtl_id", 303957)
    
    # Allow manual override input
    col_target_l, col_target_r = st.columns([3, 1])
    with col_target_l:
        target_dtl_id = int(st.number_input("Investigate Recommendation DTL ID", value=int(default_dtl), step=1))
    with col_target_r:
        st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
        if st.button("Load Project Record"):
            st.session_state["selected_dtl_id"] = target_dtl_id
            st.rerun()

    # Retrieve work record
    master_df = load_canonical_master_df()
    if not master_df.empty:
        work_match = master_df[master_df["work_recommendation_dtl_id"] == target_dtl_id]
        if work_match.empty:
            st.warning(f"Work recommendation DTL ID {target_dtl_id} not found in master corpus. Showing top critical project.")
            work_record = master_df.iloc[0].to_dict()
        else:
            work_record = work_match.iloc[0].to_dict()
    else:
        # Fallback from portfolio
        work_record = {"work_recommendation_dtl_id": target_dtl_id, "amount_recommended": 500000.0}

    # Evaluate using fitted engines and authoritative summary availability
    peer_eng, stat_eng, mismatch_eng, dup_eng, fusion_eng = load_fitted_engines()

    if peer_eng is not None:
        p_res = peer_eng.evaluate_work(work_record)
        s_res = stat_eng.evaluate_work(work_record)
        m_res = mismatch_eng.evaluate_work(work_record)
        
        # Check authoritative duplicate availability from summary truth
        auth_match = df_portfolio[df_portfolio["work_recommendation_dtl_id"] == target_dtl_id] if not df_portfolio.empty else pd.DataFrame()
        if not auth_match.empty and pd.isna(auth_match.iloc[0].get("duplicate_score")):
            d_res = {
                "score": None,
                "available": False,
                "top_matches": [],
                "match_count_likely": 0,
                "match_count_possible": 0,
                "candidates_evaluated": 0,
                "reason_codes": ["DUPLICATE_NO_BLOCK_CANDIDATES"],
                "evidence": "Duplicate detection unavailable: no comparable candidate works in contextual block.",
                "coverage": "block_empty"
            }
        else:
            d_res = dup_eng.evaluate_work(work_record)

        work_risk = fusion_eng.fuse(work_record, p_res, s_res, m_res, d_res)
    else:
        work_risk = None

    if work_risk:
        # 1. AT A GLANCE (Hero Case Dossier Header with Large Risk Block)
        st.markdown(render_case_dossier_header_html(work_risk), unsafe_allow_html=True)

        # 2. WHY THIS RISK EXISTS (WHY IS THIS WORK FLAGGED?)
        st.markdown("#### 🔍 Why Is This Work Flagged?")
        st.markdown(synthesize_plain_language_narrative(work_risk, p_res, s_res, m_res, d_res), unsafe_allow_html=True)

        # 3. WHICH ENGINES CONTRIBUTED (TOP RISK DRIVERS)
        st.markdown("#### ⚡ Top Risk Drivers")
        st.markdown(render_risk_drivers_html(work_risk, p_res, s_res, m_res, d_res), unsafe_allow_html=True)

        # 4. HOW THE RISK SCORE WAS BUILT (Engine Contribution Math Table)
        st.markdown(render_math_breakdown_html(work_risk), unsafe_allow_html=True)

        # 5. SUPPORTING TECHNICAL EVIDENCE (Expandable Accordions — Collapsed by Default)
        st.markdown("#### 🔬 Supporting Technical Evidence")
        st.markdown("Detailed diagnostic distributions, cohort calculations, and provenance verification:")

        # Expander 1: Peer Benchmarking
        with st.expander("▾ View Peer Benchmark Evidence (Cohort & Distribution)"):
            p_score = work_risk.module_scores.get("peer_benchmarking")
            p_badge = get_risk_badge_html('PEER', p_score) if p_score is not None else '<span style="color: #8b949e;">UNAVAILABLE</span>'
            st.markdown(f"""
            <div style="background: #0d1117; border: 1px solid #21262d; border-radius: 6px; padding: 12px 16px; margin-bottom: 10px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <strong style="color: #f0f6fc; font-size: 0.95rem;">Peer Benchmarking Engine (Locked Base Weight: 30%)</strong>
                    {p_badge}
                </div>
                <div style="font-size: 0.85rem; color: #c9d1d9; line-height: 1.5; margin-bottom: 8px;">
                    {p_res.get('evidence')}
                </div>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 10px; font-size: 0.8rem; color: #8b949e; border-top: 1px solid #21262d; padding-top: 8px;">
                    <div>Cohort Level: <strong style="color: #f0f6fc;">Step {p_res.get('cohort_level')}: {p_res.get('cohort_level_name')}</strong></div>
                    <div>Cohort Size (n): <strong style="color: #f0f6fc;">{p_res.get('cohort_size')}</strong></div>
                    <div>Peer Median: <strong style="color: #f0f6fc;">{format_inr(p_res.get('peer_median'))}</strong></div>
                    <div>Peer IQR: <strong style="color: #f0f6fc;">{format_inr(p_res.get('peer_iqr'))}</strong></div>
                    <div>Percentile Rank: <strong style="color: #58a6ff;">{p_res.get('percentile_rank') or 0:.1f}th</strong></div>
                    <div>Reason Codes: <code style="color: #79c0ff;">{', '.join(p_res.get('reason_codes', []))}</code></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # Expander 2: Statistical Outliers
        with st.expander("▾ View Statistical Outlier Evidence (Modified Z-Score Features)"):
            s_score = work_risk.module_scores.get("statistical_outliers")
            s_badge = get_risk_badge_html('STAT', s_score) if s_score is not None else '<span style="color: #8b949e;">UNAVAILABLE</span>'
            st.markdown(f"""
            <div style="background: #0d1117; border: 1px solid #21262d; border-radius: 6px; padding: 12px 16px; margin-bottom: 10px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <strong style="color: #f0f6fc; font-size: 0.95rem;">Statistical Outlier Engine (Locked Base Weight: 25%)</strong>
                    {s_badge}
                </div>
                <div style="font-size: 0.85rem; color: #c9d1d9; line-height: 1.5; margin-bottom: 8px;">
                    {s_res.get('evidence')}
                </div>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 10px; font-size: 0.8rem; color: #8b949e; border-top: 1px solid #21262d; padding-top: 8px;">
                    <div>Features Evaluated: <strong style="color: #f0f6fc;">{s_res.get('features_available')}/{s_res.get('features_total')}</strong></div>
                    <div>Zero-Dispersion Safety: <strong style="color: #3fb950;">ACTIVE</strong></div>
                    <div>Coverage Status: <strong style="color: #58a6ff;">{s_res.get('coverage')}</strong></div>
                    <div>Reason Codes: <code style="color: #79c0ff;">{', '.join(s_res.get('reason_codes', []))}</code></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # Expander 3: Financial-Execution Mismatch
        with st.expander("▾ View Financial–Execution Mismatch Evidence"):
            m_score = work_risk.module_scores.get("financial_execution_mismatch")
            m_badge = get_risk_badge_html('MISMATCH', m_score) if m_score is not None else '<span style="color: #8b949e;">UNAVAILABLE</span>'
            m_conf = m_res.get("confidence_label", "Level 1 (LOW)")
            st.markdown(f"""
            <div style="background: #0d1117; border: 1px solid #21262d; border-radius: 6px; padding: 12px 16px; margin-bottom: 10px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <strong style="color: #f0f6fc; font-size: 0.95rem;">Financial–Execution Mismatch Engine (Locked Base Weight: 30%)</strong>
                    {m_badge}
                </div>
                <div style="font-size: 0.85rem; color: #c9d1d9; line-height: 1.5; margin-bottom: 8px;">
                    {m_res.get('evidence', 'Financial disbursement and completion realization analysis.')}
                </div>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 10px; font-size: 0.8rem; color: #8b949e; border-top: 1px solid #21262d; padding-top: 8px;">
                    <div>Confidence Tier: <strong style="color: #58a6ff;">{m_conf}</strong></div>
                    <div>Availability: <strong style="color: {'#3fb950' if m_res.get('available') else '#8b949e'};">{'AVAILABLE' if m_res.get('available') else 'UNAVAILABLE_IN_SOURCE'}</strong></div>
                    <div>Disbursement Status: <strong style="color: #f0f6fc;">{format_inr(work_record.get('total_disbursed_amount'))}</strong></div>
                    <div>Reason Codes: <code style="color: #79c0ff;">{', '.join(m_res.get('reason_codes', []))}</code></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # Expander 4: Duplicate & Overlap Candidate Evidence
        with st.expander("▾ View Contextual Duplicate / Overlap Evidence"):
            st.markdown(render_duplicate_comparison_html(work_record, d_res), unsafe_allow_html=True)
            if len(d_res.get("top_matches", [])) > 1:
                st.markdown("##### Additional Contextual Candidates")
                dup_table = []
                for m in d_res["top_matches"][1:]:
                    m_dtl = m.get("matched_work_dtl_id")
                    m_dtl_str = str(int(float(m_dtl))) if m_dtl is not None and str(m_dtl) != "" else ""
                    dup_table.append({
                        "Candidate DTL ID": m_dtl_str,
                        "Classification": str(m.get("classification") or ""),
                        "Semantic Cosine": f"{float(m.get('semantic_cosine_similarity', 0.0)):.3f}",
                        "Agency Similarity": f"{float(m.get('agency_similarity', 0.0)):.1f}%",
                        "Same MP": "Yes" if m.get("same_mp") else "No",
                        "Candidate Description": str(m.get("matched_work_description") or "")[:120]
                    })
                st.dataframe(pd.DataFrame(dup_table), use_container_width=True, hide_index=True)

        # 6. RISK JOURNEY (Authentic Milestone Progression)
        st.markdown("#### 🛣️ Authentic Milestone Progression")
        st.markdown(render_milestone_timeline_html(work_record), unsafe_allow_html=True)

        st.markdown("---")

        # 7. WHAT SHOULD BE CHECKED? (INVESTIGATION ACTIONS)
        st.markdown("### 📋 What Should Be Checked?")
        st.markdown(
            "Concrete, objective field and administrative verification checks based on the recorded anomalies. "
            "Tailored for desk review auditors and field inspection teams."
        )

        desk_actions = [a for a in work_risk.investigation_actions if any(k in a.lower() for k in ("desk", "order", "document", "estimate", "approval", "sanction", "voucher", "disbursement"))]
        field_actions = [a for a in work_risk.investigation_actions if a not in desk_actions]

        col_act_l, col_act_r = st.columns(2)
        with col_act_l:
            st.markdown("##### 📁 Administrative & Desk Review Protocol")
            if desk_actions:
                for act in desk_actions:
                    st.markdown(f'<div class="action-box">📄 {act}</div>', unsafe_allow_html=True)
            else:
                for act in work_risk.investigation_actions[:len(work_risk.investigation_actions)//2 or 1]:
                    st.markdown(f'<div class="action-box">📄 {act}</div>', unsafe_allow_html=True)

        with col_act_r:
            st.markdown("##### 📍 Field Inspection & Asset Verification Protocol")
            if field_actions:
                for act in field_actions:
                    st.markdown(f'<div class="action-box-field">🔍 {act}</div>', unsafe_allow_html=True)
            else:
                for act in work_risk.investigation_actions[len(work_risk.investigation_actions)//2 or 1:]:
                    st.markdown(f'<div class="action-box-field">🔍 {act}</div>', unsafe_allow_html=True)


# =============================================================================
# D. COMPARE / OVERLAP
# =============================================================================

with tab_compare:
    st.markdown("### ⚖️ Project Overlap & Contextual Duplicate Comparison")
    st.markdown("Deep contextual semantic comparison and implementing agency overlap audit.")

    # Selection for comparison
    curated_overlap_options = [
        "133166 — Dharwad, Karnataka (Community Bhavan)",
        "133167 — Dharwad, Karnataka (Community Hall)",
        "298980 — Dharwad, Karnataka (Community Bhavan Pry 1/A)",
        "292696 — Dharwad, Karnataka (Cultural Bhavan)",
        "303957 — Saran, Bihar (Modern Indoor Stadium - No Duplicate)"
    ]
    
    col_comp_l, col_comp_r = st.columns([3, 1])
    with col_comp_l:
        sel_curated = st.selectbox("Curated Overlap Test Cases", curated_overlap_options, index=0)
        curated_id = int(sel_curated.split("—")[0].strip())
    with col_comp_r:
        comp_dtl = int(st.number_input("Or Input Custom DTL ID", value=int(st.session_state.get("selected_dtl_id", curated_id)), step=1))

    active_comp_id = comp_dtl

    master_df = load_canonical_master_df()
    if not master_df.empty:
        comp_match = master_df[master_df["work_recommendation_dtl_id"] == active_comp_id]
        if not comp_match.empty:
            c_record = comp_match.iloc[0].to_dict()
        else:
            st.warning(f"DTL ID {active_comp_id} not found in master corpus. Using curated sample.")
            c_record = master_df[master_df["work_recommendation_dtl_id"] == 133166].iloc[0].to_dict()
    else:
        c_record = {"work_recommendation_dtl_id": active_comp_id}

    _, _, _, dup_eng_comp, _ = load_fitted_engines()
    if dup_eng_comp is not None:
        comp_d_res = dup_eng_comp.evaluate_work(c_record)
        st.markdown(render_duplicate_comparison_html(c_record, comp_d_res), unsafe_allow_html=True)
        
        # If multiple matches exist, show table of additional matches
        if len(comp_d_res.get("top_matches", [])) > 1:
            st.markdown("#### 📑 Additional Block Overlap Candidates")
            extra_table = []
            for m in comp_d_res["top_matches"][1:]:
                m_dtl = m.get("matched_work_dtl_id")
                m_dtl_str = str(int(float(m_dtl))) if m_dtl is not None and str(m_dtl) != "" else ""
                extra_table.append({
                    "Candidate DTL ID": m_dtl_str,
                    "Classification": str(m.get("classification") or ""),
                    "Semantic Cosine": f"{float(m.get('semantic_cosine_similarity', 0.0)):.3f}",
                    "Agency Match": f"{float(m.get('agency_similarity', 0.0)):.1f}%",
                    "Same MP": "Yes" if m.get("same_mp") else "No",
                    "Candidate Description": str(m.get("matched_work_description") or "")[:120]
                })
            st.dataframe(pd.DataFrame(extra_table), use_container_width=True, hide_index=True)

        st.markdown("""
        <div style="background-color: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 14px 16px; margin-top: 14px;">
            <div style="font-size: 0.85rem; font-weight: 700; color: #58a6ff; text-transform: uppercase; margin-bottom: 4px;">
                Investigative Guidance for Overlap Candidates
            </div>
            <div style="font-size: 0.82rem; color: #c9d1d9; line-height: 1.5;">
                • <strong>Do NOT treat as confirmed fraud:</strong> In public infrastructure, similar titles frequently arise when work is sanctioned in phases, split across financial years, or funded jointly across multiple programs.<br>
                • <strong>Field Inspection Requirement:</strong> Auditors should verify whether distinct physical foundations exist at the recorded village or GPS landmark before making administrative determinations.
            </div>
        </div>
        """, unsafe_allow_html=True)


# =============================================================================
# E. ANALYZE YOUR DATASET (LIVE INGESTION & COMPATIBLE SCREENING)
# =============================================================================

with tab_dataset:
    st.markdown("### 📁 Analyze Your Dataset")
    st.markdown(
        "Independent, local-memory multi-engine screening and availability-normalized fusion "
        "for external MPLADS, State Local Area Development, or public infrastructure project datasets."
    )

    # Dynamic workflow step indicator
    user_df = st.session_state.get("user_input_df")
    has_results = "user_scored_results" in st.session_state and bool(st.session_state["user_scored_results"])
    has_data = user_df is not None and not user_df.empty

    step1_style = "color: #38bdf8; font-weight: 700;" if not has_data else "color: #10b981; font-weight: 700;"
    step2_style = "color: #38bdf8; font-weight: 700;" if (has_data and not has_results) else ("color: #10b981; font-weight: 700;" if has_results else "color: #64748b;")
    step3_style = "color: #38bdf8; font-weight: 700;" if (has_data and not has_results) else ("color: #10b981; font-weight: 700;" if has_results else "color: #64748b;")
    step4_style = "color: #38bdf8; font-weight: 700;" if (has_data and not has_results) else ("color: #10b981; font-weight: 700;" if has_results else "color: #64748b;")
    step5_style = "color: #38bdf8; font-weight: 700;" if has_results else "color: #64748b;"

    s1_icon = "✓" if has_data else "1"
    s2_icon = "✓" if has_data else "2"
    s3_icon = "✓" if has_data else "3"
    s4_icon = "✓" if has_results else "4"
    s5_icon = "★" if has_results else "5"

    st.markdown(clean_html(f"""
    <div style="background: #0d1117; border: 1px solid #1e293b; border-radius: 8px; padding: 12px 18px; margin: 12px 0 20px 0;">
        <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px; font-size: 0.76rem;">
            <span style="{step1_style}">[{s1_icon}] 01 UPLOAD</span>
            <span style="color: #475569;">➔</span>
            <span style="{step2_style}">[{s2_icon}] 02 VALIDATE & MAP</span>
            <span style="color: #475569;">➔</span>
            <span style="{step3_style}">[{s3_icon}] 03 DETECT ENGINES</span>
            <span style="color: #475569;">➔</span>
            <span style="{step4_style}">[{s4_icon}] 04 SCREEN & FUSE</span>
            <span style="color: #475569;">➔</span>
            <span style="{step5_style}">[{s5_icon}] 05 RESULTS</span>
        </div>
    </div>
    """), unsafe_allow_html=True)

    # -------------------------------------------------------------------------
    # 01. UPLOAD & DATASET SELECTION
    # -------------------------------------------------------------------------
    st.markdown("#### 01. Upload Dataset or Load Demo")
    
    col_up_l, col_up_r = st.columns([3, 1])
    with col_up_l:
        uploaded_file = st.file_uploader(
            "Upload Infrastructure Dataset (.csv, .xlsx, .parquet)",
            type=["csv", "xlsx", "parquet"],
            help="Upload structured files containing public work recommendations, sanctions, or expenditure records.",
            key="user_dataset_uploader"
        )
    with col_up_r:
        st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
        demo_clicked = st.button("📊 Load Demo Dataset (10 Works)", use_container_width=True)

    sample_csv = (
        "work_recommendation_dtl_id,unique_work_number,state,constituency,district,block_name,category,work_description,amount_recommended,amount_sanctioned,sanction_date,work_stage\n"
        "303957,WS/MP620/2024-2025/303957,Bihar,SARAN,SARAN,Amnaur,Normal/Others,Construction of Community Facility,10000000,10000000,2024-08-14,Pending for Sanction\n"
        "133166,WS/MP620/2024-2025/133166,Karnataka,DHARWAD,DHARWAD,Navalgund,Community Hall,Construction of Community Hall,497000,497000,2024-06-10,Physical Inspection\n"
        "133301,WS/MP620/2024-2025/133301,Karnataka,DHARWAD,DHARWAD,Navalgund,Community Hall,Construction of Community Hall at Village,497000,497000,2024-06-10,Completed\n"
    )
    col_dl, col_clr = st.columns([3, 1])
    with col_dl:
        st.download_button(
            label="📥 Download Canonical Data Template (CSV)",
            data=sample_csv,
            file_name="mpprisma_canonical_template.csv",
            mime="text/csv",
            use_container_width=False
        )
    with col_clr:
        if has_data:
            if st.button("🗑️ Reset / Clear Dataset", use_container_width=True):
                st.session_state.pop("user_input_df", None)
                st.session_state.pop("user_dataset_meta", None)
                st.session_state.pop("user_scored_results", None)
                st.rerun()

    # Ingestion handling
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith(".csv"):
                user_df = pd.read_csv(uploaded_file)
            elif uploaded_file.name.endswith(".parquet"):
                user_df = pd.read_parquet(uploaded_file)
            else:
                user_df = pd.read_excel(uploaded_file)
            
            curr_meta = st.session_state.get("user_dataset_meta", {})
            if curr_meta.get("source_name") != uploaded_file.name:
                st.session_state.pop("user_scored_results", None)

            st.session_state["user_input_df"] = user_df
            st.session_state["user_dataset_meta"] = {
                "source_name": uploaded_file.name,
                "is_demo": False,
                "row_count": len(user_df),
                "col_count": len(user_df.columns)
            }
        except Exception as e:
            st.error(f"⚠️ Unable to parse uploaded file: {str(e)[:160]}. Please verify the file format.")
            user_df = None

    elif demo_clicked:
        master_df = load_canonical_master_df()
        if not master_df.empty:
            cols_avail = [c for c in [
                "work_recommendation_dtl_id", "unique_work_number", "state", "constituency",
                "district", "block_name", "category", "work_description", "amount_recommended",
                "amount_sanctioned", "sanction_date", "work_stage"
            ] if c in master_df.columns]
            demo_df = master_df.head(10)[cols_avail].copy()
            st.session_state["user_input_df"] = demo_df
            st.session_state["user_dataset_meta"] = {
                "source_name": "Pre-configured 10-Work Demonstration Cohort",
                "is_demo": True,
                "row_count": len(demo_df),
                "col_count": len(demo_df.columns)
            }
            st.session_state.pop("user_scored_results", None)
            user_df = demo_df
            st.rerun()
    elif "user_input_df" in st.session_state:
        user_df = st.session_state["user_input_df"]

    if user_df is not None and user_df.empty:
        st.warning("⚠️ The uploaded dataset contains 0 records. Please upload a dataset with at least one record.")
        user_df = None

    if user_df is not None and not user_df.empty:
        meta = st.session_state.get("user_dataset_meta", {})
        source_label = meta.get("source_name", "Uploaded File")
        demo_badge = " • DEMONSTRATION DATASET" if meta.get("is_demo") else " • USER-UPLOADED DATA"
        
        preview_cols = list(user_df.columns)[:8]
        preview_cols_str = ", ".join([f"<code>{c}</code>" for c in preview_cols])
        if len(user_df.columns) > 8:
            preview_cols_str += "..."

        st.markdown(clean_html(f"""
        <div style="background: #111827; border: 1px solid #1e293b; border-left: 4px solid #38bdf8; border-radius: 6px; padding: 12px 16px; margin: 14px 0;">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
                <div>
                    <span style="font-size: 0.72rem; font-weight: 700; color: #38bdf8; text-transform: uppercase; letter-spacing: 0.6px;">Active Ingested Dataset{demo_badge}</span>
                    <div style="font-size: 1.05rem; font-weight: 700; color: #f8fafc; margin-top: 2px;">{source_label}</div>
                </div>
                <div style="display: flex; gap: 14px; font-size: 0.82rem; color: #94a3b8;">
                    <div>Rows: <strong style="color: #f8fafc;">{len(user_df):,}</strong></div>
                    <div>Columns: <strong style="color: #f8fafc;">{len(user_df.columns)}</strong></div>
                </div>
            </div>
            <div style="font-size: 0.75rem; color: #64748b; margin-top: 6px;">
                Detected Fields: {preview_cols_str}
            </div>
        </div>
        """), unsafe_allow_html=True)

        # ---------------------------------------------------------------------
        # 02. VALIDATE & MAP
        # ---------------------------------------------------------------------
        st.markdown("---")
        st.markdown("#### 02. Validate Schema & Map Compatible Columns")
        st.markdown(
            "Inspect how your dataset fields align with the canonical data model. "
            "Columns are mapped safely without inventing missing values or fabricating source fields."
        )

        col_map = {str(c).strip().lower(): c for c in user_df.columns}

        mapping_definitions = [
            ("amount_recommended", "Recommended Cost", ["amount_recommended", "recommended_amount", "amount", "cost", "sanction_amount_proposed", "estimated_cost", "work_cost"], "Required for 3 engines (Peer, Stat, Mismatch)"),
            ("district", "District", ["district", "dist", "district_name"], "Required for local peer benchmarking"),
            ("category", "Work Category", ["category", "work_category", "sector", "work_type"], "Required for peer benchmarking cohort matching"),
            ("state", "State", ["state", "state_name"], "Optional — Fallback state/regional cohort level"),
            ("work_description", "Work Description", ["work_description", "description", "title", "work_name", "work_detail"], "Required for contextual duplicate/overlap engine"),
            ("block_name", "Block / Agency", ["block_name", "block", "ida_name_raw", "implementing_agency", "agency"], "Required for duplicate blocking candidate generation"),
            ("sanction_date", "Sanction Date", ["sanction_date", "sanctioned_date", "date_sanctioned", "admin_sanction_date"], "Optional — Enhances financial mismatch & timeline analysis"),
            ("amount_sanctioned", "Sanctioned Cost", ["amount_sanctioned", "sanctioned_amount", "sanction_amount"], "Optional — Enhances outlier cost ratios & financial mismatch"),
            ("work_recommendation_dtl_id", "Record Identifier", ["work_recommendation_dtl_id", "dtl_id", "work_id", "unique_work_number", "id", "recommendation_id"], "Optional — Work identifier for audit traceability")
        ]

        mapping_rows = []
        mapped_concepts = {}
        for std_key, concept_title, aliases, role_desc in mapping_definitions:
            matched_col = None
            for alias in aliases:
                if alias in col_map:
                    matched_col = col_map[alias]
                    break
            
            if matched_col is not None:
                mapped_concepts[std_key] = matched_col
                status_badge = "✅ Mapped"
            elif "Required" in role_desc:
                status_badge = "⚠️ Missing (Engine Dependency)"
            else:
                status_badge = "ℹ️ Not Provided (Optional)"

            mapping_rows.append({
                "Canonical Field": concept_title,
                "Source Column": str(matched_col) if matched_col else "—",
                "Role / Dependency": role_desc,
                "Mapping Status": status_badge
            })

        st.dataframe(pd.DataFrame(mapping_rows), use_container_width=True, hide_index=True)
        
        mapped_count = len(mapped_concepts)
        total_concepts = len(mapping_definitions)
        st.markdown(
            f"<div style='font-size: 0.8rem; color: #94a3b8; margin-top: 4px;'>"
            f"Validation Status: <strong style='color: #10b981;'>{mapped_count} of {total_concepts}</strong> canonical concepts mapped. "
            f"Missing fields are excluded rather than filled with synthetic defaults."
            f"</div>",
            unsafe_allow_html=True
        )

        # ---------------------------------------------------------------------
        # 03. COMPATIBLE ENGINE DETECTION
        # ---------------------------------------------------------------------
        st.markdown("---")
        st.markdown("#### 03. Engine Compatibility Matrix")
        st.markdown(
            "Evaluation of which official MPPrisma analytical engines can safely run on the mapped dataset fields. "
            "Engines with missing dependencies are excluded from fusion."
        )

        has_amt = "amount_recommended" in mapped_concepts
        has_dist = "district" in mapped_concepts
        has_cat = "category" in mapped_concepts
        has_st = "state" in mapped_concepts
        has_desc = "work_description" in mapped_concepts
        has_block = "block_name" in mapped_concepts
        has_sanc_date = "sanction_date" in mapped_concepts
        has_sanc_amt = "amount_sanctioned" in mapped_concepts

        compat_peer = has_amt and has_cat and (has_dist or has_st)
        compat_stat = has_amt
        compat_mis = has_amt and (has_sanc_date or has_sanc_amt)
        compat_dup = has_desc and (has_block or has_dist)

        compat_rows = [
            {
                "Engine Module": "1. Peer Benchmarking (30% base weight)",
                "Required Evidence": "amount_recommended, category, district/state",
                "Status": "✅ COMPATIBLE" if compat_peer else "❌ INCOMPATIBLE",
                "Operational Context": "Evaluates cost percentile against historical cohorts" if compat_peer else "Requires numeric recommended cost and category"
            },
            {
                "Engine Module": "2. Statistical Outliers (25% base weight)",
                "Required Evidence": "amount_recommended",
                "Status": "✅ COMPATIBLE" if compat_stat else "❌ INCOMPATIBLE",
                "Operational Context": "Evaluates Modified Z-Scores across numeric distributions" if compat_stat else "Requires positive numeric cost"
            },
            {
                "Engine Module": "3. Financial–Execution Mismatch (30% base weight)",
                "Required Evidence": "amount_recommended, sanction_date / amount_sanctioned",
                "Status": "✅ COMPATIBLE" if compat_mis else "❌ INCOMPATIBLE",
                "Operational Context": "Detects timing delays and financial sanction divergence" if compat_mis else "Requires sanction date or sanctioned amount"
            },
            {
                "Engine Module": "4. Duplicate / Overlap (15% base weight)",
                "Required Evidence": "work_description, block_name / district",
                "Status": "✅ COMPATIBLE" if compat_dup else "❌ INCOMPATIBLE",
                "Operational Context": "Calculates semantic cosine similarity on contextual blocks" if compat_dup else "Requires textual description and block/district for blocking"
            }
        ]
        st.dataframe(pd.DataFrame(compat_rows), use_container_width=True, hide_index=True)

        compat_count = sum([compat_peer, compat_stat, compat_mis, compat_dup])
        if compat_count == 0:
            st.error("❌ Incompatible Schema: None of the 4 risk engines can operate on the detected columns. Please supply at least 'amount_recommended' or 'work_description'.")
        else:
            st.markdown(clean_html(f"""
            <div style="background: rgba(56, 189, 248, 0.08); border: 1px solid rgba(56, 189, 248, 0.25); border-radius: 6px; padding: 10px 14px; margin: 10px 0; font-size: 0.8rem; color: #94a3b8;">
                ⚡ <strong>{compat_count} of 4 Engines Ready:</strong> Availability-normalized fusion will distribute 100% of the composite weight proportionally across active engines. Inactive engines are strictly excluded from the denominator.
            </div>
            """), unsafe_allow_html=True)

        # ---------------------------------------------------------------------
        # 04. SCREEN & FUSE
        # ---------------------------------------------------------------------
        st.markdown("---")
        st.markdown("#### 04. Execute Screening & Evidence Fusion")
        
        if compat_count > 0:
            btn_label = f"🚀 Screen Dataset with {compat_count} Compatible Engine{'s' if compat_count > 1 else ''}"
            if st.button(btn_label, use_container_width=False):
                with st.spinner("Executing multi-engine screening and availability-normalized fusion..."):
                    peer_eng, stat_eng, mismatch_eng, dup_eng, fusion_eng = load_fitted_engines()
                    
                    std_df = user_df.copy()
                    for std_k, mapped_source in mapped_concepts.items():
                        if mapped_source in user_df.columns and std_k not in std_df.columns:
                            std_df[std_k] = user_df[mapped_source]

                    if "amount_recommended" in std_df.columns:
                        std_df["amount_recommended"] = pd.to_numeric(std_df["amount_recommended"], errors="coerce")

                    total_rows = len(std_df)
                    eval_cap = min(100, total_rows)
                    eval_rows = std_df.head(eval_cap)

                    prog_bar = st.progress(0, text=f"Screening 0 of {eval_cap} records...")
                    results_list = []

                    for idx, (_, r) in enumerate(eval_rows.iterrows()):
                        row_dict = r.to_dict()
                        p_res = peer_eng.evaluate_work(row_dict) if compat_peer and peer_eng else {"available": False, "score": None}
                        s_res = stat_eng.evaluate_work(row_dict) if compat_stat and stat_eng else {"available": False, "score": None}
                        m_res = mismatch_eng.evaluate_work(row_dict) if compat_mis and mismatch_eng else {"available": False, "score": None}
                        d_res = dup_eng.evaluate_work(row_dict) if compat_dup and dup_eng else {"available": False, "score": None}

                        if fusion_eng:
                            w_risk = fusion_eng.fuse(row_dict, p_res, s_res, m_res, d_res)
                            cov = w_risk.evidence_coverage.get("available_weight_pct", 100.0)
                            active_mods = [k for k, v in w_risk.module_scores.items() if v is not None]
                            raw_wid = row_dict.get("unique_work_number") or row_dict.get("work_recommendation_dtl_id") or f"USER_{idx+1}"
                            
                            dist_str = str(row_dict.get("district") or "").strip()
                            state_str = str(row_dict.get("state") or "").strip()
                            loc_str = f"{dist_str}, {state_str}".strip(", ") if (dist_str or state_str) else "—"

                            results_list.append({
                                "Rank": idx + 1,
                                "Work / DTL ID": str(raw_wid),
                                "State / District": loc_str,
                                "Category": str(row_dict.get("category") or "—"),
                                "Amount": format_inr(row_dict.get("amount_recommended")),
                                "Risk Score": f"{w_risk.risk_score:.2f}" if w_risk.risk_score is not None else "—",
                                "Risk Band": w_risk.risk_band,
                                "Coverage": f"{cov:.0f}%",
                                "Active Engines": f"{len(active_mods)}/4",
                                "_risk_score_raw": w_risk.risk_score if w_risk.risk_score is not None else 0.0
                            })
                        prog_bar.progress((idx + 1) / eval_cap, text=f"Screening {idx+1} of {eval_cap} records...")

                    prog_bar.empty()
                    st.session_state["user_scored_results"] = results_list
                    st.rerun()

        # ---------------------------------------------------------------------
        # 05. RESULTS
        # ---------------------------------------------------------------------
        if "user_scored_results" in st.session_state and st.session_state["user_scored_results"]:
            st.markdown("---")
            st.markdown("#### 05. Screening Results & Evidence Dossier")

            st.markdown("""
            <div style="background: linear-gradient(180deg, #161b22 0%, #0d1117 100%); border: 2px solid #38bdf8; border-radius: 8px; padding: 16px 20px; margin: 12px 0 20px 0;">
                <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px; margin-bottom: 6px;">
                    <span style="background: rgba(56, 189, 248, 0.15); color: #38bdf8; border: 1px solid #38bdf8; padding: 2px 10px; border-radius: 9999px; font-size: 0.75rem; font-weight: 800; letter-spacing: 0.8px; text-transform: uppercase;">
                        ⚠️ USER-PROVIDED DATA • NOT OFFICIAL MPLADS RECORDS
                    </span>
                    <span style="font-size: 0.75rem; color: #94a3b8; background: #21262d; padding: 2px 8px; border-radius: 4px;">
                        Data Partition: Local Memory Only
                    </span>
                </div>
                <div style="font-size: 0.85rem; color: #c9d1d9; line-height: 1.45;">
                    The composite risk scores, severity tiers, and evidence items below are derived exclusively from user-uploaded records. This analysis is completely segregated and <strong>does not modify official 18th Lok Sabha MPLADS datasets, portfolio metrics, or statutory queues.</strong>
                </div>
            </div>
            """, unsafe_allow_html=True)

            res_data = st.session_state["user_scored_results"]
            df_user_res = pd.DataFrame(res_data)

            u_total = len(df_user_res)
            u_crit = int((df_user_res["Risk Band"] == "CRITICAL").sum())
            u_high = int((df_user_res["Risk Band"] == "HIGH").sum())
            u_med = int((df_user_res["Risk Band"] == "MEDIUM").sum())
            u_low = int((df_user_res["Risk Band"] == "LOW").sum())
            u_avg = df_user_res["_risk_score_raw"].mean()

            col_k1, col_k2, col_k3, col_k4 = st.columns(4)
            with col_k1:
                st.markdown(get_metric_card_html("User Works Screened", f"{u_total:,}", subtext="Processed locally"), unsafe_allow_html=True)
            with col_k2:
                st.markdown(get_metric_card_html("Priority Review Cohort", f"{u_crit + u_high:,}", subtext=f"Critical: {u_crit} | High: {u_high}", border_color="#ef4444" if (u_crit + u_high) > 0 else "#30363d"), unsafe_allow_html=True)
            with col_k3:
                st.markdown(get_metric_card_html("Mean Risk Score", f"{u_avg:.1f} / 100", subtext="Availability-normalized", border_color="#38bdf8"), unsafe_allow_html=True)
            with col_k4:
                st.markdown(get_metric_card_html("Low Risk / Baseline", f"{u_low:,}", subtext=f"{u_low/max(1,u_total)*100:.1f}% conforming", border_color="#10b981"), unsafe_allow_html=True)

            st.markdown(f"""
            <div style="background: #0d1117; border: 1px solid #1e293b; border-radius: 6px; padding: 12px 16px; margin: 12px 0 16px 0;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <span style="font-size: 0.74rem; font-weight: 700; color: #94a3b8; text-transform: uppercase;">Risk Severity Distribution</span>
                    <div style="display: flex; gap: 12px; font-size: 0.74rem;">
                        <span style="color: #ef4444; font-weight: 600;">Critical: {u_crit}</span>
                        <span style="color: #f97316; font-weight: 600;">High: {u_high}</span>
                        <span style="color: #eab308; font-weight: 600;">Medium: {u_med}</span>
                        <span style="color: #10b981; font-weight: 600;">Low: {u_low}</span>
                    </div>
                </div>
                <div style="display: flex; height: 8px; border-radius: 4px; overflow: hidden; background: #1e293b;">
                    <div style="width: {u_crit/max(1,u_total)*100}%; background: #ef4444;"></div>
                    <div style="width: {u_high/max(1,u_total)*100}%; background: #f97316;"></div>
                    <div style="width: {u_med/max(1,u_total)*100}%; background: #eab308;"></div>
                    <div style="width: {u_low/max(1,u_total)*100}%; background: #10b981;"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("##### Scored Work Queue")
            show_cols = [c for c in df_user_res.columns if not c.startswith("_")]
            st.dataframe(df_user_res[show_cols], use_container_width=True, hide_index=True)

            col_exp_l, col_exp_r = st.columns([3, 1])
            with col_exp_l:
                csv_export = df_user_res[show_cols].to_csv(index=False)
                st.download_button(
                    label="📥 Export Scored Results as CSV",
                    data=csv_export,
                    file_name="mpprisma_user_scored_results.csv",
                    mime="text/csv"
                )

    st.markdown("""
    <div style="background-color: rgba(16, 185, 129, 0.08); border-left: 3px solid #10b981; padding: 10px 14px; border-radius: 0 4px 4px 0; margin-top: 20px; font-size: 0.8rem; color: #c9d1d9;">
        🔒 <strong>Data Privacy & Local Execution Guarantee:</strong> All dataset validation, feature extraction, and evidence fusion operations execute strictly within local session memory. Uploaded files are never transmitted to external APIs or third-party servers, and are automatically purged when your session terminates.
    </div>
    """, unsafe_allow_html=True)


# =============================================================================
# F. METHODOLOGY & PROVENANCE
# =============================================================================

with tab_meta:
    st.markdown("### ℹ️ MPPrisma Platform Architecture & Methodology")

    # Visual Architecture Flow Diagram
    st.markdown("""
    <div class="investigation-card">
        <div style="font-size: 0.8rem; font-weight: 700; color: #58a6ff; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 12px;">
            End-to-End Architectural Data Flow
        </div>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 10px;">
            <div style="background: #0d1117; border: 1px solid #21262d; border-top: 3px solid #58a6ff; border-radius: 6px; padding: 12px;">
                <div style="font-size: 0.72rem; color: #58a6ff; font-weight: 700; text-transform: uppercase;">1. Source Data</div>
                <div style="color: #f0f6fc; font-weight: 600; font-size: 0.88rem; margin: 3px 0;">MoSPI Pre-Login APIs</div>
                <div style="font-size: 0.76rem; color: #8b949e;">18th Lok Sabha official public dumps.</div>
            </div>
            <div style="background: #0d1117; border: 1px solid #21262d; border-top: 3px solid #3fb950; border-radius: 6px; padding: 12px;">
                <div style="font-size: 0.72rem; color: #3fb950; font-weight: 700; text-transform: uppercase;">2. Canonicalization</div>
                <div style="color: #f0f6fc; font-weight: 600; font-size: 0.88rem; margin: 3px 0;">Exact Primary Joins</div>
                <div style="font-size: 0.76rem; color: #8b949e;">106,261 works, 99.6% join via DTL_ID.</div>
            </div>
            <div style="background: #0d1117; border: 1px solid #21262d; border-top: 3px solid #d29922; border-radius: 6px; padding: 12px;">
                <div style="font-size: 0.72rem; color: #d29922; font-weight: 700; text-transform: uppercase;">3. Core Engines</div>
                <div style="color: #f0f6fc; font-weight: 600; font-size: 0.88rem; margin: 3px 0;">Four Detectors</div>
                <div style="font-size: 0.76rem; color: #8b949e;">Peer (30%), Stat (25%), Mismatch (30%), Dup (15%).</div>
            </div>
            <div style="background: #0d1117; border: 1px solid #21262d; border-top: 3px solid #db6d28; border-radius: 6px; padding: 12px;">
                <div style="font-size: 0.72rem; color: #db6d28; font-weight: 700; text-transform: uppercase;">4. Evidence Fusion</div>
                <div style="color: #f0f6fc; font-weight: 600; font-size: 0.88rem; margin: 3px 0;">Normalized Math</div>
                <div style="font-size: 0.76rem; color: #8b949e;">Dynamic reweighting across available detectors.</div>
            </div>
            <div style="background: #0d1117; border: 1px solid #21262d; border-top: 3px solid #da3633; border-radius: 6px; padding: 12px;">
                <div style="font-size: 0.72rem; color: #da3633; font-weight: 700; text-transform: uppercase;">5. Risk Profiling</div>
                <div style="color: #f0f6fc; font-weight: 600; font-size: 0.88rem; margin: 3px 0;">Standardized Bands</div>
                <div style="font-size: 0.76rem; color: #8b949e;">LOW, MEDIUM, HIGH, CRITICAL.</div>
            </div>
            <div style="background: #0d1117; border: 1px solid #21262d; border-top: 3px solid #a371f7; border-radius: 6px; padding: 12px;">
                <div style="font-size: 0.72rem; color: #a371f7; font-weight: 700; text-transform: uppercase;">6. Investigation</div>
                <div style="color: #f0f6fc; font-weight: 600; font-size: 0.88rem; margin: 3px 0;">Actionable Dossiers</div>
                <div style="font-size: 0.76rem; color: #8b949e;">Desk audit & field inspection protocols.</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="investigation-card">
        <h4 style="color: #58a6ff; margin-top: 0;">Authoritative Source Provenance</h4>
        <p style="color: #c9d1d9; font-size: 0.9rem; line-height: 1.5;">
            All intelligence, risk scores, and evaluation outputs in <strong>MPPrisma</strong> are produced strictly from authentic Government of India 
            Ministry of Statistics and Programme Implementation (MoSPI) MPLADS pre-login API responses for the <strong>18th Lok Sabha</strong>.
        </p>
        <table style="width: 100%; font-size: 0.85rem; color: #c9d1d9; border-collapse: collapse; margin-top: 10px;">
            <thead>
                <tr style="border-bottom: 1px solid #30363d; text-align: left;">
                    <th style="padding: 8px;">Dataset Name</th>
                    <th style="padding: 8px;">Records</th>
                    <th style="padding: 8px;">Join Key</th>
                    <th style="padding: 8px;">Exact Match Coverage</th>
                </tr>
            </thead>
            <tbody>
                <tr style="border-bottom: 1px solid #21262d;">
                    <td style="padding: 8px;"><code>works_recommended.json</code></td>
                    <td style="padding: 8px;">106,261</td>
                    <td style="padding: 8px;">WORK_RECOMMENDATION_DTL_ID</td>
                    <td style="padding: 8px;">100.0% (Base Population)</td>
                </tr>
                <tr style="border-bottom: 1px solid #21262d;">
                    <td style="padding: 8px;"><code>works_completed.json</code></td>
                    <td style="padding: 8px;">34,259</td>
                    <td style="padding: 8px;">WORK_RECOMMENDATION_DTL_ID</td>
                    <td style="padding: 8px;">99.62% (34,129 exact joined, 130 orphans documented)</td>
                </tr>
                <tr style="border-bottom: 1px solid #21262d;">
                    <td style="padding: 8px;"><code>expenditure_completed_ongoing.json</code></td>
                    <td style="padding: 8px;">83,907</td>
                    <td style="padding: 8px;">WORK_RECOMMENDATION_DTL_ID</td>
                    <td style="padding: 8px;">99.57% (83,546 exact joined)</td>
                </tr>
            </tbody>
        </table>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="investigation-card">
        <h4 style="color: #58a6ff; margin-top: 0;">The Four Locked Core Analytical Engines</h4>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; margin-top: 10px;">
            <div style="background-color: #0d1117; padding: 12px; border-radius: 6px; border: 1px solid #21262d;">
                <strong style="color: #f0f6fc;">1. Peer Benchmarking (30%)</strong>
                <p style="font-size: 0.8rem; color: #8b949e; margin-top: 4px;">
                    5-step fallback cohort hierarchy (district-cat-yr → district-cat → state-cat-yr → state-cat → national). Minimum target: 10 peers. Robust median/IQR.
                </p>
            </div>
            <div style="background-color: #0d1117; padding: 12px; border-radius: 6px; border: 1px solid #21262d;">
                <strong style="color: #f0f6fc;">2. Statistical Outliers (25%)</strong>
                <p style="font-size: 0.8rem; color: #8b949e; margin-top: 4px;">
                    Robust Modified Z-scores based on Median and Median Absolute Deviation (MAD). Zero-dispersion safety ensures identical rates do not trigger false alarms.
                </p>
            </div>
            <div style="background-color: #0d1117; padding: 12px; border-radius: 6px; border: 1px solid #21262d;">
                <strong style="color: #f0f6fc;">3. Financial Mismatch (30%)</strong>
                <p style="font-size: 0.8rem; color: #8b949e; margin-top: 4px;">
                    3-tier confidence hierarchy: Level 1 proxy (LOW), Level 1 financial (MEDIUM), Level 2 time (HIGH), Level 3 physical (VERY HIGH, strictly UNAVAILABLE).
                </p>
            </div>
            <div style="background-color: #0d1117; padding: 12px; border-radius: 6px; border: 1px solid #21262d;">
                <strong style="color: #f0f6fc;">4. Duplicate / Overlap (15%)</strong>
                <p style="font-size: 0.8rem; color: #8b949e; margin-top: 4px;">
                    Contextual candidate blocking + all-MiniLM-L6-v2 dense semantic cosine similarity + RapidFuzz agency matching. Tri-state classification.
                </p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="investigation-card">
        <h4 style="color: #58a6ff; margin-top: 0;">Availability-Normalized Evidence Fusion Mathematics</h4>
        <p style="color: #c9d1d9; font-size: 0.88rem; line-height: 1.5;">
            Missing modules are never assumed to be zero risk. The composite risk score dynamically normalizes across active detectors:
        </p>
        <div style="background-color: #0d1117; border: 1px solid #21262d; border-radius: 6px; padding: 12px; margin: 10px 0; font-family: monospace; font-size: 0.88rem; color: #79c0ff;">
            Risk Score = Σ(w_m · S_m) / Σ_{m ∈ Available} w_m<br>
            Coverage % = (Σ_{m ∈ Available} w_m) × 100%
        </div>
        <p style="color: #8b949e; font-size: 0.82rem; line-height: 1.4;">
            This prevents artificial score depression in early-stage projects where expenditure or completion records have not yet been generated.
        </p>
    </div>
    """, unsafe_allow_html=True)
