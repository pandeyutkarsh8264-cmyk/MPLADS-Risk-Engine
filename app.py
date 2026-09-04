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
    get_metric_card_html,
    RISK_COLORS
)
from src.peer_benchmark import PeerBenchmarkEngine
from src.statistical_outliers import StatisticalOutlierEngine
from src.mismatch import FinancialExecutionMismatchEngine
from src.duplicate_overlap import DuplicateOverlapEngine
from src.fusion import RiskFusionEngine, WorkRisk

# Page Configuration
st.set_page_config(
    page_title="MPLADS Risk Intelligence Command Center",
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
            <h1 style="font-size: 1.85rem; margin: 4px 0 6px 0; color: #f0f6fc; letter-spacing: -0.5px;">
                MPLADS Risk Intelligence & Investigation Engine
            </h1>
            <div style="font-size: 0.85rem; color: #8b949e;">
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
# MAIN NAVIGATION TABS
# =============================================================================

tab_exec, tab_queue, tab_investigate, tab_dist, tab_meta = st.tabs([
    "📊 Executive Dashboard",
    "📋 Ranked Risk Queue",
    "🔍 Work Investigation View",
    "📈 Risk Distributions",
    "ℹ️ Methodology & Provenance"
])


# =============================================================================
# TAB 1: EXECUTIVE DASHBOARD
# =============================================================================

with tab_exec:
    st.markdown("### 🏛️ Portfolio Executive Overview")
    st.markdown(
        "Real-time screening KPIs computed across the active 18th Lok Sabha MPLADS works "
        "using availability-normalized multi-engine evidence fusion."
    )

    # Calculate actual computed portfolio metrics
    crit_count = int((df_filtered["risk_band"] == "CRITICAL").sum())
    high_count = int((df_filtered["risk_band"] == "HIGH").sum())
    med_count = int((df_filtered["risk_band"] == "MEDIUM").sum())
    low_count = int((df_filtered["risk_band"] == "LOW").sum())
    scored_count = int(df_filtered["risk_score"].notna().sum())
    
    avg_score = df_filtered["risk_score"].dropna().mean() if scored_count > 0 else 0.0
    avg_coverage = df_filtered["available_weight_pct"].dropna().mean() if len(df_filtered) > 0 else 0.0
    priority_count = crit_count + high_count

    # KPI Cards Row 1
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1:
        st.markdown(get_metric_card_html("Total Screened Works", f"{len(df_filtered):,}", f"Computed scores: {scored_count:,}"), unsafe_allow_html=True)
    with kpi2:
        st.markdown(get_metric_card_html("Priority Investigation", f"{priority_count:,}", "Critical + High priority works", border_color="#da3633"), unsafe_allow_html=True)
    with kpi3:
        st.markdown(get_metric_card_html("Avg Risk Score", f"{avg_score:.1f} / 100", "Availability-normalized", border_color="#58a6ff"), unsafe_allow_html=True)
    with kpi4:
        st.markdown(get_metric_card_html("Avg Evidence Coverage", f"{avg_coverage:.1f}%", "Active locked module weight", border_color="#238636"), unsafe_allow_html=True)

    # KPI Cards Row 2 (Risk Bands)
    b1, b2, b3, b4 = st.columns(4)
    with b1:
        st.markdown(get_metric_card_html("Critical Risk (80–100)", f"{crit_count:,}", f"{(crit_count/max(1, len(df_filtered))*100):.2f}% of portfolio", border_color="#da3633"), unsafe_allow_html=True)
    with b2:
        st.markdown(get_metric_card_html("High Risk (60–79)", f"{high_count:,}", f"{(high_count/max(1, len(df_filtered))*100):.2f}% of portfolio", border_color="#db6d28"), unsafe_allow_html=True)
    with b3:
        st.markdown(get_metric_card_html("Medium Risk (30–59)", f"{med_count:,}", f"{(med_count/max(1, len(df_filtered))*100):.1f}% of portfolio", border_color="#d29922"), unsafe_allow_html=True)
    with b4:
        st.markdown(get_metric_card_html("Low Risk (0–29)", f"{low_count:,}", f"{(low_count/max(1, len(df_filtered))*100):.1f}% of portfolio", border_color="#238636"), unsafe_allow_html=True)

    st.markdown("---")

    # Fast Executive Summary Section
    col_summary_l, col_summary_r = st.columns([3, 2])
    with col_summary_l:
        st.markdown("#### 🚨 Immediate Attention Highlights")
        # Top 5 highest risk works in current selection
        top_critical = df_filtered.sort_values(by="risk_score", ascending=False).head(5)
        for _, row in top_critical.iterrows():
            r_score = row.get("risk_score")
            r_band = row.get("risk_band")
            raw_wid = row.get("work_id")
            raw_dtl = row.get("work_recommendation_dtl_id")
            dtl_disp = int(float(raw_dtl)) if pd.notna(raw_dtl) and str(raw_dtl) not in ("nan", "None", "") else "UNKNOWN"
            w_id = str(raw_wid) if pd.notna(raw_wid) and str(raw_wid) not in ("nan", "None", "") else f"DTL_{dtl_disp}"
            desc = row.get("work_description") or ""
            mp = row.get("mp_name") or ""
            loc = f"{row.get('constituency')}, {row.get('state')}"
            rec_amt = format_inr(row.get("amount_recommended"))
            
            st.markdown(f"""
            <div style="background-color: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 12px 16px; margin-bottom: 8px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div style="font-weight: 700; color: #f0f6fc; font-size: 0.95rem;">{w_id}</div>
                    <div>{get_risk_badge_html(r_band, r_score)}</div>
                </div>
                <div style="font-size: 0.85rem; color: #8b949e; margin: 4px 0;">{desc[:120]}...</div>
                <div style="display: flex; justify-content: space-between; font-size: 0.78rem; color: #c9d1d9;">
                    <span>👤 {mp} • 📍 {loc}</span>
                    <span>💰 Recommended: <strong>{rec_amt}</strong></span>
                </div>
            </div>
            """, unsafe_allow_html=True)

    with col_summary_r:
        st.markdown("#### ⚖️ Evidence Integrity Principle")
        st.markdown("""
        <div style="background-color: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px;">
            <div style="font-size: 0.95rem; font-weight: 600; color: #58a6ff; margin-bottom: 8px;">
                Availability-Normalized Scoring
            </div>
            <div style="font-size: 0.85rem; color: #c9d1d9; line-height: 1.5;">
                Missing/unavailable modules are strictly <strong>excluded from the denominator</strong> rather than treated as zero.
            </div>
            <div style="background-color: #0d1117; border: 1px solid #21262d; border-radius: 6px; padding: 10px; margin: 10px 0; font-family: monospace; font-size: 0.8rem; color: #79c0ff;">
                Risk Score = Σ(w_m · S_m) / Σ(w_m)<br>
                Coverage % = Σ(w_m) × 100%
            </div>
            <div style="font-size: 0.8rem; color: #8b949e; line-height: 1.4;">
                • <strong>Risk Score ≠ Evidence Coverage</strong><br>
                • Level 3 Physical Progress is strictly <code>UNAVAILABLE_IN_SOURCE</code> (never fabricated).<br>
                • Missing expenditure is treated as data unavailability, not financial compliance.
            </div>
        </div>
        """, unsafe_allow_html=True)


# =============================================================================
# TAB 2: RANKED RISK QUEUE
# =============================================================================

with tab_queue:
    st.markdown("### 📋 Ranked Portfolio Risk Queue")
    st.markdown("Sortable register of evaluated projects prioritized by composite risk score.")

    col_sort_l, col_sort_r = st.columns([2, 1])
    with col_sort_l:
        top_n = st.selectbox("Display Count", [50, 100, 250, 500, "All Matching"], index=0)
    with col_sort_r:
        sort_order = st.selectbox("Sort Order", ["Risk Score (Highest First)", "Recommended Amount (Highest First)", "Evidence Coverage (Lowest First)"])

    # Apply sorting
    df_sorted = df_filtered.copy()
    if "Risk Score" in sort_order:
        df_sorted = df_sorted.sort_values(by="risk_score", ascending=False)
    elif "Recommended Amount" in sort_order:
        df_sorted = df_sorted.sort_values(by="amount_recommended", ascending=False)
    elif "Coverage" in sort_order:
        df_sorted = df_sorted.sort_values(by="available_weight_pct", ascending=True)

    if top_n != "All Matching":
        df_display = df_sorted.head(int(top_n))
    else:
        df_display = df_sorted

    # Format table columns cleanly
    table_rows = []
    for rank, (_, r) in enumerate(df_display.iterrows(), start=1):
        raw_wid = r.get("work_id")
        raw_dtl = r.get("work_recommendation_dtl_id")
        dtl_num = int(float(raw_dtl)) if pd.notna(raw_dtl) and str(raw_dtl) not in ("nan", "None", "") else None
        dtl_disp = str(dtl_num) if dtl_num is not None else "—"
        wid = str(raw_wid) if pd.notna(raw_wid) and str(raw_wid) not in ("nan", "None", "") else f"DTL_{dtl_disp}"
        table_rows.append({
            "Rank": rank,
            "Work ID": wid,
            "DTL ID": dtl_disp,
            "State": str(r.get("state") or ""),
            "Constituency": str(r.get("constituency") or ""),
            "Category": str(r.get("category") or ""),
            "Recommended": format_inr(r.get("amount_recommended")),
            "Risk Score": f"{r.get('risk_score'):.2f}" if pd.notna(r.get("risk_score")) else "—",
            "Risk Band": str(r.get("risk_band") or "UNAVAILABLE"),
            "Coverage %": f"{r.get('available_weight_pct'):.0f}%",
            "Peer (30%)": f"{r.get('peer_score'):.1f}" if pd.notna(r.get("peer_score")) else "—",
            "Stat (25%)": f"{r.get('stat_score'):.1f}" if pd.notna(r.get("stat_score")) else "—",
            "Mismatch (30%)": f"{r.get('mismatch_score'):.1f}" if pd.notna(r.get("mismatch_score")) else "—",
            "Duplicate (15%)": f"{r.get('duplicate_score'):.1f}" if pd.notna(r.get("duplicate_score")) else "—",
            "_dtl_id_num": dtl_num,
        })

    df_view = pd.DataFrame(table_rows)
    cols_to_show = [c for c in df_view.columns if not c.startswith("_")]
    st.dataframe(df_view[cols_to_show], use_container_width=True, hide_index=True, height=450)

    # Quick selector to send work directly to Investigation View
    st.markdown("#### 🔎 Select a Project for Investigation Deep Dive")
    if not df_display.empty and table_rows:
        opts = [f"#{r['Rank']} - {r['Work ID']} (Score: {r['Risk Score']}, Band: {r['Risk Band']}) | {r['State']}" for r in table_rows]
        sel_idx = st.selectbox("Choose work from queue", range(len(opts)), format_func=lambda i: opts[i], index=0)
        sel_dtl_id = table_rows[sel_idx].get("_dtl_id_num")
        
        if st.button("🚀 Open in Work Investigation View"):
            if sel_dtl_id is not None:
                st.session_state["selected_dtl_id"] = int(sel_dtl_id)
                st.success(f"Selected Work DTL ID: {int(sel_dtl_id)}. Switch to 'Work Investigation View' tab.")
            else:
                st.warning("Selected record does not have a valid DTL ID.")


# =============================================================================
# TAB 3: WORK INVESTIGATION VIEW (DEEP DIVE)
# =============================================================================

with tab_investigate:
    st.markdown("### 🔍 Dedicated Project Investigation Deep Dive")
    st.markdown("Comprehensive evidence inspection, multi-engine breakdown, and objective field/desk review actions.")

    # Determine which work to investigate
    target_dtl_id = st.session_state.get("selected_dtl_id", 303957)
    
    # Allow manual override input
    col_target_l, col_target_r = st.columns([3, 1])
    with col_target_l:
        manual_dtl = st.number_input("Investigate Recommendation DTL ID", value=int(target_dtl_id), step=1)
    with col_target_r:
        st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
        if st.button("Load Project Record"):
            target_dtl_id = manual_dtl
            st.session_state["selected_dtl_id"] = manual_dtl

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
        # Fallback mock work risk
        work_risk = None

    if work_risk:
        # Work Identification Header
        meta = work_risk.work_metadata
        raw_wid = work_risk.work_id
        raw_dtl = meta.get('work_recommendation_dtl_id')
        dtl_disp = int(float(raw_dtl)) if pd.notna(raw_dtl) and str(raw_dtl) not in ("nan", "None", "") else "UNKNOWN"
        w_id = str(raw_wid) if pd.notna(raw_wid) and str(raw_wid) not in ("nan", "None", "") else f"DTL_{dtl_disp}"
        r_score = work_risk.risk_score
        r_band = work_risk.risk_band
        cov = work_risk.evidence_coverage

        st.markdown(f"""
        <div class="investigation-card">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap;">
                <div>
                    <div style="font-size: 0.8rem; font-weight: 700; color: #58a6ff; letter-spacing: 1px; text-transform: uppercase;">
                        PROJECT INVESTIGATION DOSSIER • DTL ID: {dtl_disp}
                    </div>
                    <h2 style="margin: 4px 0 8px 0; color: #f0f6fc; font-size: 1.45rem;">
                        {w_id}
                    </h2>
                    <div style="font-size: 1rem; color: #e6edf3; margin-bottom: 12px; line-height: 1.4;">
                        {meta.get('work_description') or 'No description provided in recommendation record.'}
                    </div>
                </div>
                <div style="text-align: right;">
                    {get_risk_badge_html(r_band, r_score)}
                    <div style="margin-top: 6px; font-size: 0.8rem; color: #8b949e;">
                        Evidence Coverage: <strong style="color: #58a6ff;">{cov.get('available_weight_pct'):.1f}%</strong>
                    </div>
                </div>
            </div>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-top: 14px; padding-top: 14px; border-top: 1px solid #30363d;">
                <div><span style="color: #8b949e; font-size: 0.75rem; text-transform: uppercase;">MP Name</span><br><strong style="color: #f0f6fc;">{meta.get('mp_name') or 'Unknown'}</strong></div>
                <div><span style="color: #8b949e; font-size: 0.75rem; text-transform: uppercase;">State & Constituency</span><br><strong style="color: #f0f6fc;">{meta.get('constituency')}, {meta.get('state')}</strong></div>
                <div><span style="color: #8b949e; font-size: 0.75rem; text-transform: uppercase;">Category</span><br><strong style="color: #f0f6fc;">{meta.get('category')}</strong></div>
                <div><span style="color: #8b949e; font-size: 0.75rem; text-transform: uppercase;">Current Stage</span><br><strong style="color: #58a6ff;">{meta.get('work_stage')}</strong></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Financial Realization Breakdown
        st.markdown("#### 💰 Financial Realization Milestones")
        f1, f2, f3, f4 = st.columns(4)
        with f1:
            st.markdown(get_metric_card_html("Recommended Amount", format_inr(meta.get("amount_recommended")), "Initial proposal"), unsafe_allow_html=True)
        with f2:
            st.markdown(get_metric_card_html("Sanctioned Amount", format_inr(meta.get("amount_sanctioned")), "Administrative approval"), unsafe_allow_html=True)
        with f3:
            st.markdown(get_metric_card_html("Completed Amount", format_inr(meta.get("amount_completed")), "Joined completed record"), unsafe_allow_html=True)
        with f4:
            st.markdown(get_metric_card_html("Disbursed Vendor Sum", format_inr(meta.get("total_disbursed_amount")), "Joined expenditure data"), unsafe_allow_html=True)

        st.markdown("---")

        # The Four Locked Engines Breakdown
        st.markdown("### 🧩 Multi-Engine Evidence Breakdown")
        
        m_col1, m_col2 = st.columns(2)
        
        # Engine 1: Peer Benchmarking
        with m_col1:
            p_score = work_risk.module_scores.get("peer_benchmarking")
            p_badge = get_risk_badge_html('PEER', p_score) if p_score is not None else '<span style="color:#8b949e;">UNAVAILABLE</span>'
            st.markdown(f"""
            <div class="module-card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <div style="font-weight: 700; color: #f0f6fc; font-size: 1rem;">
                        1. Peer Benchmarking (30%)
                    </div>
                    <div>{p_badge}</div>
                </div>
                <div style="font-size: 0.82rem; color: #8b949e; margin-bottom: 8px;">
                    Cohort Level: <strong>Step {p_res.get('cohort_level')}: {p_res.get('cohort_level_name')} (n={p_res.get('cohort_size')})</strong>
                </div>
                <div style="font-size: 0.85rem; color: #c9d1d9; line-height: 1.4; background-color: #0d1117; padding: 10px; border-radius: 6px; border: 1px solid #21262d;">
                    {p_res.get('evidence')}
                </div>
                <div style="margin-top: 8px; font-size: 0.78rem; color: #8b949e;">
                    Cohort Median: <strong>{format_inr(p_res.get('peer_median'))}</strong> • IQR: <strong>{format_inr(p_res.get('peer_iqr'))}</strong> • Percentile: <strong>{p_res.get('percentile_rank') or 0:.1f}th</strong>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # Engine 2: Statistical Outliers
        with m_col2:
            s_score = work_risk.module_scores.get("statistical_outliers")
            s_badge = get_risk_badge_html('STAT', s_score) if s_score is not None else '<span style="color:#8b949e;">UNAVAILABLE</span>'
            st.markdown(f"""
            <div class="module-card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <div style="font-weight: 700; color: #f0f6fc; font-size: 1rem;">
                        2. Statistical Outliers (25%)
                    </div>
                    <div>{s_badge}</div>
                </div>
                <div style="font-size: 0.82rem; color: #8b949e; margin-bottom: 8px;">
                    Features Evaluated: <strong>{s_res.get('features_available')}/{s_res.get('features_total')} (Status: {s_res.get('coverage')})</strong>
                </div>
                <div style="font-size: 0.85rem; color: #c9d1d9; line-height: 1.4; background-color: #0d1117; padding: 10px; border-radius: 6px; border: 1px solid #21262d;">
                    {s_res.get('evidence')}
                </div>
                <div style="margin-top: 8px; font-size: 0.78rem; color: #8b949e;">
                    Zero-dispersion safety active. Missing numeric features excluded from composite.
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<div style='margin-top: 12px;'></div>", unsafe_allow_html=True)
        m_col3, m_col4 = st.columns(2)

        # Engine 3: Financial-Execution Mismatch
        with m_col3:
            m_score = work_risk.module_scores.get("financial_execution_mismatch")
            m_conf = m_res.get("confidence_label", "NONE")
            m_badge = get_risk_badge_html('MISMATCH', m_score) if m_score is not None else '<span style="color:#8b949e;">UNAVAILABLE</span>'
            st.markdown(f"""
            <div class="module-card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <div style="font-weight: 700; color: #f0f6fc; font-size: 1rem;">
                        3. Financial–Execution Mismatch (30%)
                    </div>
                    <div>{m_badge}</div>
                </div>
                <div style="font-size: 0.82rem; color: #8b949e; margin-bottom: 8px;">
                    Evidence Tier: {get_confidence_badge_html(m_conf)}
                </div>
                <div style="font-size: 0.85rem; color: #c9d1d9; line-height: 1.4; background-color: #0d1117; padding: 10px; border-radius: 6px; border: 1px solid #21262d;">
                    {m_res.get('evidence')}
                </div>
                <div style="margin-top: 8px; font-size: 0.78rem; color: #8b949e;">
                    Level 3 Physical Progress: <span style="color: #db6d28; font-weight: 600;">UNAVAILABLE_IN_SOURCE</span> (Strictly Not Fabricated).
                </div>
            </div>
            """, unsafe_allow_html=True)

        # Engine 4: Duplicate / Overlap
        with m_col4:
            d_score = work_risk.module_scores.get("duplicate_overlap")
            d_badge = get_risk_badge_html('DUP', d_score) if d_score is not None else '<span style="color:#8b949e;">UNAVAILABLE</span>'
            st.markdown(f"""
            <div class="module-card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <div style="font-weight: 700; color: #f0f6fc; font-size: 1rem;">
                        4. Duplicate / Overlap Detection (15%)
                    </div>
                    <div>{d_badge}</div>
                </div>
                <div style="font-size: 0.82rem; color: #8b949e; margin-bottom: 8px;">
                    Method: <strong>all-MiniLM-L6-v2 Embeddings + RapidFuzz Entity Similarity</strong>
                </div>
                <div style="font-size: 0.85rem; color: #c9d1d9; line-height: 1.4; background-color: #0d1117; padding: 10px; border-radius: 6px; border: 1px solid #21262d;">
                    {d_res.get('evidence')}
                </div>
                <div style="margin-top: 8px; font-size: 0.78rem; color: #8b949e;">
                    Candidates Evaluated: <strong>{d_res.get('candidates_evaluated', 0)}</strong> within contextual candidate block.
                </div>
            </div>
            """, unsafe_allow_html=True)

        # Duplicate Matches Detail (if any matches found)
        if d_res.get("top_matches"):
            st.markdown("##### 👥 Contextual Duplicate Candidate Pairings")
            dup_table = []
            for m in d_res["top_matches"]:
                m_dtl = m.get("matched_work_dtl_id")
                m_dtl_str = str(int(float(m_dtl))) if m_dtl is not None and str(m_dtl) != "" else ""
                dup_table.append({
                    "Matched DTL ID": m_dtl_str,
                    "Classification": str(m.get("classification") or ""),
                    "Semantic Cosine": f"{float(m.get('semantic_cosine_similarity', 0.0)):.3f}",
                    "Agency Similarity": f"{float(m.get('agency_similarity', 0.0)):.1f}%",
                    "Same MP": "Yes" if m.get("same_mp") else "No",
                    "Similar Cost": "Yes" if m.get("similar_amount") else "No",
                    "Matched Description": str(m.get("matched_work_description") or "")[:120]
                })
            st.dataframe(pd.DataFrame(dup_table), use_container_width=True, hide_index=True)

        st.markdown("---")

        # Concrete Investigation Actions Section
        st.markdown("### 📋 Recommended Investigation Next Steps")
        st.markdown(
            "Concrete, objective field and administrative verification checks based on the recorded anomalies. "
            "Designed for field inspection officers and desk auditors."
        )

        for act in work_risk.investigation_actions:
            st.markdown(f"""
            <div class="action-box">
                👉 {act}
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")

        # Expandable Evidence Items and Traceability
        with st.expander("🔬 Evidence Traceability & Source Provenance Details"):
            st.markdown(
                "Every score is mathematically bound to verifiable source evidence items from the GoI API responses."
            )
            ev_table = []
            for item in work_risk.evidence_items:
                sc = item.get("score")
                sc_str = f"{float(sc):.1f}" if sc is not None else "—"
                ev_table.append({
                    "Module": str(item.get("module") or ""),
                    "Metric": str(item.get("metric") or ""),
                    "Available": "Yes" if item.get("available") else "No",
                    "Score": sc_str,
                    "Confidence": str(item.get("confidence") or "NONE"),
                    "Observed Value": str(item.get("observed_value") or "")[:60],
                    "Comparison Norm": str(item.get("comparison_value") or "")[:40],
                    "Source Dataset": str(item.get("source_dataset") or ""),
                    "Data Quality Flags": ", ".join(item.get("data_quality_flags", []))
                })
            st.dataframe(pd.DataFrame(ev_table), use_container_width=True, hide_index=True)


# =============================================================================
# TAB 4: RISK DISTRIBUTIONS
# =============================================================================

with tab_dist:
    st.markdown("### 📈 Portfolio Risk Distributions")
    st.markdown("Statistical distribution of risk scores, evidence coverage, and geographical patterns.")

    col_ch1, col_ch2 = st.columns(2)

    with col_ch1:
        st.markdown("#### Risk Band Composition")
        band_counts = df_filtered["risk_band"].value_counts().reindex(["CRITICAL", "HIGH", "MEDIUM", "LOW"]).fillna(0)
        st.bar_chart(band_counts, color="#58a6ff")

    with col_ch2:
        st.markdown("#### Evidence Coverage Distribution (%)")
        st.line_chart(df_filtered["available_weight_pct"].value_counts().sort_index(), color="#3fb950")

    st.markdown("---")

    col_ch3, col_ch4 = st.columns(2)

    with col_ch3:
        st.markdown("#### Top States by Priority Investigation Works (Critical + High)")
        high_works = df_filtered[df_filtered["risk_band"].isin(["CRITICAL", "HIGH"])]
        if not high_works.empty:
            state_risk_counts = high_works["state"].value_counts().head(10)
            st.bar_chart(state_risk_counts, color="#da3633")
        else:
            st.info("No Critical or High risk works in current filter selection.")

    with col_ch4:
        st.markdown("#### Risk Severity across Work Categories")
        cat_risk = df_filtered.groupby("category")["risk_score"].mean().sort_values(ascending=False).head(10)
        st.bar_chart(cat_risk, color="#d29922")


# =============================================================================
# TAB 5: DATA QUALITY, METHODOLOGY & PROVENANCE
# =============================================================================

with tab_meta:
    st.markdown("### ℹ️ Methodology, Data Quality & Architecture")
    
    st.markdown("""
    <div class="investigation-card">
        <h4 style="color: #58a6ff; margin-top: 0;">Authoritative Source Provenance</h4>
        <p style="color: #c9d1d9; font-size: 0.9rem; line-height: 1.5;">
            All intelligence and evaluation outputs are produced strictly from authentic Government of India 
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
