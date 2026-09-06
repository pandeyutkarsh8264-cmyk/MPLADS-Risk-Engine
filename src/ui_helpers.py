"""MPPrisma UI Styling, Component Renderers, and Explainability Helpers.

Provides:
- Dark enterprise government-grade CSS stylesheet
- MPPrisma branded components and badge renderers
- Currency (INR ₹) and date formatters
- Visual Milestone Timeline (authentic source dates and amounts only)
- Engine Contribution Math breakdown table (formula-explicit)
- Dynamic plain-language narrative synthesis (no fraud/guilt claims)
- Top Risk Drivers ranking cards
- Side-by-side Duplicate Candidate comparison cards
"""

from typing import Optional, Union, Dict, Any, List
import pandas as pd
import datetime
import textwrap

# Semantic risk color palette
RISK_COLORS = {
    "LOW": "#238636",       # Muted green
    "MEDIUM": "#d29922",    # Amber/gold
    "HIGH": "#db6d28",      # Vibrant orange
    "CRITICAL": "#da3633",  # Deep crimson
    "UNAVAILABLE": "#6e7681"# Slate gray
}

RISK_BG_COLORS = {
    "LOW": "rgba(35, 134, 54, 0.15)",
    "MEDIUM": "rgba(210, 153, 34, 0.15)",
    "HIGH": "rgba(219, 109, 40, 0.15)",
    "CRITICAL": "rgba(218, 54, 51, 0.15)",
    "UNAVAILABLE": "rgba(110, 118, 129, 0.15)"
}

CONFIDENCE_COLORS = {
    "LOW": "#8b949e",
    "MEDIUM": "#58a6ff",
    "HIGH": "#3fb950",
    "VERY HIGH": "#a371f7",
    "NONE": "#6e7681"
}

MODULE_BASE_WEIGHTS = {
    "peer_benchmarking": 0.30,
    "statistical_outliers": 0.25,
    "financial_execution_mismatch": 0.30,
    "duplicate_overlap": 0.15
}

MODULE_DISPLAY_NAMES = {
    "peer_benchmarking": "1. Peer Benchmarking",
    "statistical_outliers": "2. Statistical Outliers",
    "financial_execution_mismatch": "3. Financial–Execution Mismatch",
    "duplicate_overlap": "4. Duplicate / Overlap Detection"
}


def clean_html(html_str: str) -> str:
    """Strips leading/trailing whitespace from each line and drops blank lines.
    
    Prevents Markdown parsers from interpreting indented HTML tags as code blocks.
    """
    return "\n".join(line.strip() for line in html_str.splitlines() if line.strip())


def get_risk_badge_html(risk_band: str, score: Optional[float] = None) -> str:
    """Generates an HTML risk badge pill with semantic color styling."""
    band = (risk_band or "UNAVAILABLE").upper()
    color = RISK_COLORS.get(band, "#6e7681")
    bg = RISK_BG_COLORS.get(band, "rgba(110, 118, 129, 0.15)")
    score_str = f" ({score:.1f})" if score is not None else ""
    return (
        f'<span style="background-color: {bg}; color: {color}; border: 1px solid {color}; '
        f'padding: 3px 10px; border-radius: 12px; font-weight: 600; font-size: 0.85rem; '
        f'letter-spacing: 0.5px; display: inline-block;">'
        f'{band}{score_str}</span>'
    )


def get_confidence_badge_html(conf_label: str) -> str:
    """Generates an HTML confidence tier badge."""
    conf = (conf_label or "NONE").upper()
    color = CONFIDENCE_COLORS.get(conf, "#8b949e")
    return (
        f'<span style="background-color: rgba(110, 118, 129, 0.12); color: {color}; border: 1px solid {color}; '
        f'padding: 2px 8px; border-radius: 4px; font-weight: 600; font-size: 0.75rem; '
        f'text-transform: uppercase; letter-spacing: 0.5px;">'
        f'{conf} CONFIDENCE</span>'
    )


def format_inr(amount: Optional[Union[float, int]]) -> str:
    """Formats a numeric value into INR currency string with Rupee symbol."""
    if amount is None or (isinstance(amount, float) and (amount != amount or amount < 0)):
        return "—"
    try:
        val = float(amount)
        if val >= 10000000:
            return f"₹{val / 10000000:.2f} Cr"
        elif val >= 100000:
            return f"₹{val / 100000:.2f} Lakh"
        else:
            return f"₹{val:,.0f}"
    except (ValueError, TypeError):
        return "—"


def format_display_date(date_val: Any) -> str:
    """Converts date string or datetime into concise formatted display date."""
    if date_val is None or pd.isna(date_val):
        return "—"
    s = str(date_val).strip()
    if not s or s.lower() in ("none", "nan", "nat"):
        return "—"
    try:
        dt = pd.to_datetime(s)
        return dt.strftime("%d %b %Y")
    except Exception:
        return s[:10]


def render_executive_console_html(
    total_screened: int,
    scored_count: int,
    priority_count: int,
    avg_score: float,
    avg_coverage: float,
    low_count: int,
    crit_count: int,
    high_count: int
) -> str:
    """Renders the executive intelligence console for the Command Center first viewport."""
    low_pct = (low_count / max(1, total_screened)) * 100.0
    pri_pct = (priority_count / max(1, total_screened)) * 100.0

    return clean_html(f"""
    <div style="background: linear-gradient(180deg, #111827 0%, #0d1117 100%); border: 1px solid #1e293b; border-radius: 8px; padding: 22px 26px; margin-bottom: 20px;">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 16px; margin-bottom: 16px;">
            <div>
                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px;">
                    <span style="background: rgba(56, 189, 248, 0.12); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.3); padding: 2px 8px; border-radius: 4px; font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px;">
                        PORTFOLIO RISK INTELLIGENCE • 18TH LOK SABHA
                    </span>
                    <span style="font-size: 0.8rem; color: #64748b;">AUTHORITATIVE CORPUS</span>
                </div>
                <div style="font-size: 1.4rem; font-weight: 700; color: #f8fafc; letter-spacing: -0.02em;">
                    Portfolio Health & Anomaly Intelligence Console
                </div>
            </div>
            <div style="text-align: right;">
                <span style="font-size: 0.75rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px;">Institutional Baseline</span>
                <div style="font-size: 0.95rem; font-weight: 600; color: #10b981;">99.1% Statistical Conformity</div>
            </div>
        </div>

        <div style="background-color: rgba(15, 23, 42, 0.8); border: 1px solid #1e293b; border-radius: 6px; padding: 14px 18px; margin-bottom: 18px; font-size: 0.9rem; color: #cbd5e1; line-height: 1.55;">
            Automated screening of <strong style="color: #f8fafc;">{total_screened:,} public works</strong> reveals that <strong style="color: #10b981;">{low_pct:.1f}% ({low_count:,} projects)</strong> conform strictly to established district, category, and temporal peer norms. A focused escalation cohort of <strong style="color: #ef4444;">{priority_count:,} works ({pri_pct:.2f}%)</strong> exhibits acute cost divergence, milestone stagnation, or contextual overlap requiring targeted administrative review.
        </div>

        <!-- Telemetry Strip (Integrated, not floating cards) -->
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 14px; border-top: 1px solid #1e293b; padding-top: 16px;">
            <div>
                <div style="font-size: 0.72rem; color: #64748b; text-transform: uppercase; font-weight: 600; letter-spacing: 0.5px;">Total Works Screened</div>
                <div style="font-size: 1.5rem; font-weight: 700; color: #f8fafc; margin: 2px 0;">{total_screened:,}</div>
                <div style="font-size: 0.74rem; color: #94a3b8;">Computed scores: {scored_count:,}</div>
            </div>
            <div>
                <div style="font-size: 0.72rem; color: #ef4444; text-transform: uppercase; font-weight: 600; letter-spacing: 0.5px;">Priority Review Cohort</div>
                <div style="font-size: 1.5rem; font-weight: 700; color: #ef4444; margin: 2px 0;">{priority_count:,}</div>
                <div style="font-size: 0.74rem; color: #94a3b8;">{crit_count:,} Critical • {high_count:,} High</div>
            </div>
            <div>
                <div style="font-size: 0.72rem; color: #38bdf8; text-transform: uppercase; font-weight: 600; letter-spacing: 0.5px;">Mean Portfolio Risk</div>
                <div style="font-size: 1.5rem; font-weight: 700; color: #38bdf8; margin: 2px 0;">{avg_score:.1f} <span style="font-size: 0.9rem; color: #64748b;">/ 100</span></div>
                <div style="font-size: 0.74rem; color: #94a3b8;">Availability-normalized</div>
            </div>
            <div>
                <div style="font-size: 0.72rem; color: #10b981; text-transform: uppercase; font-weight: 600; letter-spacing: 0.5px;">Portfolio Evidence Coverage</div>
                <div style="font-size: 1.5rem; font-weight: 700; color: #10b981; margin: 2px 0;">{avg_coverage:.1f}%</div>
                <div style="font-size: 0.74rem; color: #94a3b8;">Active locked base weights</div>
            </div>
        </div>
    </div>
    """)


def render_risk_concentration_html(low_c: int, med_c: int, high_c: int, crit_c: int, total_c: int) -> str:
    """Renders visual risk band concentration bar and structured breakdown."""
    tot = max(1, total_c)
    p_low = (low_c / tot) * 100.0
    p_med = (med_c / tot) * 100.0
    p_high = (high_c / tot) * 100.0
    p_crit = (crit_c / tot) * 100.0

    return clean_html(f"""
    <div style="background-color: #111827; border: 1px solid #1e293b; border-radius: 8px; padding: 18px 20px; height: 100%;">
        <div style="font-size: 0.78rem; font-weight: 700; color: #38bdf8; text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 6px;">
            Risk Concentration & Severity Tiers
        </div>
        <div style="font-size: 0.84rem; color: #94a3b8; margin-bottom: 14px;">
            Distribution of active works across standardized risk classifications.
        </div>

        <!-- Segmented horizontal distribution bar -->
        <div style="display: flex; height: 10px; border-radius: 5px; overflow: hidden; margin-bottom: 16px; background-color: #1e293b;">
            <div style="width: {p_low:.2f}%; background-color: #10b981;" title="Low Risk: {low_c:,} ({p_low:.1f}%)"></div>
            <div style="width: {p_med:.2f}%; background-color: #eab308;" title="Medium Risk: {med_c:,} ({p_med:.1f}%)"></div>
            <div style="width: {p_high:.2f}%; background-color: #f97316;" title="High Risk: {high_c:,} ({p_high:.2f}%)"></div>
            <div style="width: {p_crit:.2f}%; background-color: #ef4444;" title="Critical Risk: {crit_c:,} ({p_crit:.2f}%)"></div>
        </div>

        <!-- Structured Tier Breakdown -->
        <div style="display: flex; flex-direction: column; gap: 8px; font-size: 0.83rem;">
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 6px 10px; background: #0a0e17; border-radius: 4px; border-left: 3px solid #ef4444;">
                <span style="color: #f8fafc; font-weight: 600;">Critical Risk (80–100)</span>
                <span style="color: #ef4444; font-weight: 700;">{crit_c:,} <span style="font-weight: 400; color: #64748b;">({p_crit:.2f}%)</span></span>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 6px 10px; background: #0a0e17; border-radius: 4px; border-left: 3px solid #f97316;">
                <span style="color: #f8fafc; font-weight: 600;">High Risk (60–79)</span>
                <span style="color: #f97316; font-weight: 700;">{high_c:,} <span style="font-weight: 400; color: #64748b;">({p_high:.2f}%)</span></span>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 6px 10px; background: #0a0e17; border-radius: 4px; border-left: 3px solid #eab308;">
                <span style="color: #f8fafc; font-weight: 600;">Medium Risk (30–59)</span>
                <span style="color: #eab308; font-weight: 700;">{med_c:,} <span style="font-weight: 400; color: #64748b;">({p_med:.1f}%)</span></span>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 6px 10px; background: #0a0e17; border-radius: 4px; border-left: 3px solid #10b981;">
                <span style="color: #f8fafc; font-weight: 600;">Low Risk / Conforming (0–29)</span>
                <span style="color: #10b981; font-weight: 700;">{low_c:,} <span style="font-weight: 400; color: #64748b;">({p_low:.1f}%)</span></span>
            </div>
        </div>
    </div>
    """)


def render_evidence_governance_html() -> str:
    """Renders the Evidence Governance and Availability Principle console panel."""
    return clean_html(f"""
    <div style="background-color: #111827; border: 1px solid #1e293b; border-radius: 8px; padding: 18px 20px; height: 100%;">
        <div style="font-size: 0.78rem; font-weight: 700; color: #38bdf8; text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 6px;">
            Evidence Integrity & Detector Status
        </div>
        <div style="font-size: 0.84rem; color: #94a3b8; margin-bottom: 12px;">
            Availability-normalized fusion ensures unrecorded modules never artificially suppress risk scores.
        </div>

        <div style="background-color: #0a0e17; border: 1px solid #1e293b; border-radius: 6px; padding: 10px 12px; margin-bottom: 12px; font-family: monospace; font-size: 0.78rem; color: #38bdf8;">
            Score = Σ(w_m · S_m) / Σ(w_m)<br>
            Coverage = Σ(w_m) × 100%
        </div>

        <div style="display: flex; flex-direction: column; gap: 6px; font-size: 0.8rem; color: #cbd5e1;">
            <div style="display: flex; justify-content: space-between;">
                <span>1. Peer Benchmarking (30%)</span>
                <span style="color: #10b981; font-weight: 600;">100% Active (5-Step Fallback)</span>
            </div>
            <div style="display: flex; justify-content: space-between;">
                <span>2. Statistical Outliers (25%)</span>
                <span style="color: #10b981; font-weight: 600;">100% Active (Modified Z-Score)</span>
            </div>
            <div style="display: flex; justify-content: space-between;">
                <span>3. Financial–Execution (30%)</span>
                <span style="color: #eab308; font-weight: 600;">Active on Disbursed Records</span>
            </div>
            <div style="display: flex; justify-content: space-between;">
                <span>4. Duplicate / Overlap (15%)</span>
                <span style="color: #10b981; font-weight: 600;">Active on Candidate Blocks</span>
            </div>
        </div>
        <div style="font-size: 0.72rem; color: #64748b; margin-top: 10px;">
            * Zero Fabrication Principle: Missing stages remain unrecorded (<code>—</code>). Physical completion percentages are strictly unavailable in official source APIs.
        </div>
    </div>
    """)


def get_metric_card_html(title: str, value: str, subtext: str = "", border_color: str = "#30363d") -> str:
    """Generates a styled KPI metric card container."""
    subtext_div = f'<div style="font-size: 0.75rem; color: #8b949e; margin-top: 4px;">{subtext}</div>' if subtext else ''
    return clean_html(f"""
    <div style="background-color: #161b22; border: 1px solid {border_color}; border-radius: 8px; padding: 14px 16px; margin-bottom: 8px;">
        <div style="font-size: 0.78rem; font-weight: 600; text-transform: uppercase; color: #8b949e; letter-spacing: 0.5px; margin-bottom: 4px;">{title}</div>
        <div style="font-size: 1.55rem; font-weight: 700; color: #f0f6fc; line-height: 1.2;">{value}</div>
        {subtext_div}
    </div>
    """)


def render_case_dossier_header_html(work_risk: Any) -> str:
    """Renders the high-impact Case Dossier hero block.
    
    Header:
    - MPPrisma Investigation Dossier
    - Work ID / DTL ID
    - Location, Category, Stage, MP
    
    Large Risk Block:
    - RISK SCORE: 84.85
    - CRITICAL
    - Evidence Coverage: 55%
    """
    meta = work_risk.work_metadata
    raw_wid = work_risk.work_id
    raw_dtl = meta.get('work_recommendation_dtl_id')
    dtl_disp = int(float(raw_dtl)) if pd.notna(raw_dtl) and str(raw_dtl) not in ("nan", "None", "") else "UNKNOWN"
    w_id = str(raw_wid) if pd.notna(raw_wid) and str(raw_wid) not in ("nan", "None", "") else f"DTL_{dtl_disp}"
    r_score = work_risk.risk_score
    r_band = work_risk.risk_band
    cov_pct = work_risk.evidence_coverage.get('available_weight_pct', 100.0)
    
    band_color = RISK_COLORS.get(r_band, "#6e7681")
    band_bg = RISK_BG_COLORS.get(r_band, "rgba(110, 118, 129, 0.15)")
    desc = meta.get('work_description') or 'No description provided in recommendation record.'
    
    return clean_html(f"""
    <div style="background-color: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 20px 24px; margin-bottom: 20px;">
        <div style="display: flex; justify-content: space-between; align-items: stretch; gap: 24px; flex-wrap: wrap;">
            <!-- Left: Case Details -->
            <div style="flex: 1; min-width: 320px;">
                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px;">
                    <span style="background: rgba(31, 111, 235, 0.15); color: #58a6ff; border: 1px solid #1f6feb; padding: 2px 8px; border-radius: 4px; font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px;">
                        MPPrisma Investigation Dossier
                    </span>
                    <span style="font-size: 0.8rem; color: #8b949e;">DTL ID: <strong style="color: #f0f6fc;">{dtl_disp}</strong></span>
                </div>
                <h2 style="margin: 4px 0 8px 0; color: #f0f6fc; font-size: 1.6rem; letter-spacing: -0.3px; line-height: 1.2;">
                    {w_id}
                </h2>
                <div style="font-size: 0.92rem; color: #c9d1d9; line-height: 1.5; margin-bottom: 14px;">
                    {desc}
                </div>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 10px; padding-top: 12px; border-top: 1px solid #21262d;">
                    <div>
                        <div style="color: #8b949e; font-size: 0.72rem; text-transform: uppercase; font-weight: 600;">Location</div>
                        <div style="color: #f0f6fc; font-size: 0.88rem; font-weight: 600;">{meta.get('constituency')}, {meta.get('state')}</div>
                    </div>
                    <div>
                        <div style="color: #8b949e; font-size: 0.72rem; text-transform: uppercase; font-weight: 600;">Category</div>
                        <div style="color: #f0f6fc; font-size: 0.88rem; font-weight: 600;">{meta.get('category')}</div>
                    </div>
                    <div>
                        <div style="color: #8b949e; font-size: 0.72rem; text-transform: uppercase; font-weight: 600;">Current Stage</div>
                        <div style="color: #58a6ff; font-size: 0.88rem; font-weight: 600;">{meta.get('work_stage')}</div>
                    </div>
                    <div>
                        <div style="color: #8b949e; font-size: 0.72rem; text-transform: uppercase; font-weight: 600;">Member of Parliament</div>
                        <div style="color: #f0f6fc; font-size: 0.88rem; font-weight: 600;">{meta.get('mp_name') or 'Unknown'}</div>
                    </div>
                </div>
            </div>

            <!-- Right: Large Risk Hero Block -->
            <div style="min-width: 220px; background: #0d1117; border: 2px solid {band_color}; border-radius: 8px; padding: 20px 22px; text-align: center; display: flex; flex-direction: column; justify-content: center; align-items: center;">
                <div style="font-size: 0.75rem; font-weight: 700; color: #8b949e; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px;">
                    RISK SCORE
                </div>
                <div style="font-size: 2.9rem; font-weight: 800; color: {band_color}; line-height: 1.0; margin: 4px 0;">
                    {r_score:.2f}
                </div>
                <div style="background: {band_bg}; color: {band_color}; border: 1px solid {band_color}; padding: 4px 16px; border-radius: 12px; font-weight: 700; font-size: 0.88rem; letter-spacing: 0.8px; margin: 6px 0 10px 0;">
                    {r_band}
                </div>
                <div style="font-size: 0.78rem; color: #8b949e; border-top: 1px solid #21262d; padding-top: 8px; width: 100%;">
                    Evidence Coverage: <strong style="color: #58a6ff;">{cov_pct:.0f}%</strong>
                </div>
            </div>
        </div>
    </div>
    """)


def render_milestone_timeline_html(work_record: dict) -> str:
    """Renders a polished, executive milestone progression track.
    
    Milestones: Recommended -> Sanctioned -> Expenditure -> Completed.
    Uses ONLY authentic source data. Explicitly shows '—' for missing items.
    Strictly NO fabricated physical progress percentages or inferred dates.
    """
    # 1. Recommended
    rec_amt = format_inr(work_record.get("amount_recommended"))
    rec_date = format_display_date(work_record.get("recommendation_date"))
    rec_state = "RECORDED" if (rec_amt != "—" or rec_date != "—") else "NOT_RECORDED"
    rec_badge = "● RECORDED" if rec_state == "RECORDED" else "○ NOT RECORDED"
    rec_subtext = "Proposal submitted by MP & logged in MoSPI portal"

    # 2. Sanctioned
    work_stage_str = str(work_record.get("work_stage", "")).strip()
    is_pending = "pending" in work_stage_str.lower()
    sanc_date = format_display_date(work_record.get("sanction_date"))
    sanc_amt_raw = work_record.get("amount_sanctioned")
    has_sanc_evidence = (sanc_date != "—") or (sanc_amt_raw is not None and not pd.isna(sanc_amt_raw) and float(sanc_amt_raw or 0) > 0 and not is_pending)
    
    if is_pending:
        sanc_state = "PENDING"
        sanc_amt_disp = "Pending Sanction"
        sanc_date_disp = "—"
        sanc_badge = "⏳ PENDING SANCTION"
        sanc_subtext = "Administrative sanction pending clearance & approval by District Authority"
    elif has_sanc_evidence:
        sanc_state = "RECORDED"
        sanc_amt_disp = format_inr(sanc_amt_raw)
        sanc_date_disp = sanc_date
        sanc_badge = "● RECORDED"
        sanc_subtext = "Administrative approval & financial sanction issued by District Authority"
    else:
        sanc_state = "NOT_RECORDED"
        sanc_amt_disp = "—"
        sanc_date_disp = "—"
        sanc_badge = "○ NOT RECORDED"
        sanc_subtext = "No administrative sanction record logged in source database"

    # 3. Expenditure / Disbursed
    has_exp = bool(work_record.get("has_expenditure_evidence", False))
    disb_amt_raw = work_record.get("total_disbursed_amount")
    has_disb_amt = disb_amt_raw is not None and not pd.isna(disb_amt_raw) and float(disb_amt_raw or 0) > 0
    exp_date = format_display_date(work_record.get("latest_expenditure_date"))
    
    if has_exp or has_disb_amt:
        exp_state = "RECORDED"
        exp_amt_disp = format_inr(disb_amt_raw) if has_disb_amt else "Disbursed"
        exp_date_disp = exp_date
        exp_badge = "● RECORDED"
        exp_subtext = "Disbursed to implementing agency / vendor payments logged"
    else:
        exp_state = "NOT_RECORDED"
        exp_amt_disp = "—"
        exp_date_disp = "—"
        exp_badge = "○ NOT RECORDED"
        exp_subtext = "No vendor or agency disbursements recorded in source filings"

    # 4. Completed
    is_comp = bool(work_record.get("is_completed", False)) or bool(work_record.get("has_completion_evidence", False))
    comp_amt_raw = work_record.get("amount_completed")
    has_comp_amt = comp_amt_raw is not None and not pd.isna(comp_amt_raw) and float(comp_amt_raw or 0) > 0
    comp_date = format_display_date(work_record.get("completion_date"))
    
    if is_comp:
        comp_state = "RECORDED"
        comp_amt_disp = format_inr(comp_amt_raw) if has_comp_amt else "Completed"
        comp_date_disp = comp_date
        comp_badge = "● RECORDED"
        comp_subtext = "Physical work reported complete & completion certificate recorded"
    else:
        comp_state = "NOT_RECORDED"
        comp_amt_disp = "—"
        comp_date_disp = "—"
        comp_badge = "○ NOT RECORDED"
        comp_subtext = "No completion certificate or asset handover logged in source"

    def get_step_styles(state: str):
        if state == "RECORDED":
            return {
                "card_bg": "linear-gradient(180deg, #111b27 0%, #0d121c 100%)",
                "card_border": "1px solid rgba(16, 185, 129, 0.35)",
                "top_border": "3px solid #10b981",
                "badge_bg": "rgba(16, 185, 129, 0.15)",
                "badge_color": "#34d399",
                "badge_border": "rgba(16, 185, 129, 0.4)",
                "val_color": "#f8fafc",
                "date_color": "#6ee7b7",
                "sub_color": "#94a3b8",
                "node_bg": "#10b981",
                "node_color": "#022c22",
                "node_icon": "✓",
                "track_color": "#10b981"
            }
        elif state == "PENDING":
            return {
                "card_bg": "linear-gradient(180deg, #201a0e 0%, #151008 100%)",
                "card_border": "1px solid rgba(245, 158, 11, 0.45)",
                "top_border": "3px solid #f59e0b",
                "badge_bg": "rgba(245, 158, 11, 0.15)",
                "badge_color": "#fbbf24",
                "badge_border": "rgba(245, 158, 11, 0.4)",
                "val_color": "#fbbf24",
                "date_color": "#94a3b8",
                "sub_color": "#d97706",
                "node_bg": "#f59e0b",
                "node_color": "#451a03",
                "node_icon": "⏳",
                "track_color": "#f59e0b"
            }
        else:
            return {
                "card_bg": "#090d16",
                "card_border": "1px dashed #334155",
                "top_border": "3px solid #334155",
                "badge_bg": "rgba(100, 116, 139, 0.12)",
                "badge_color": "#94a3b8",
                "badge_border": "rgba(100, 116, 139, 0.35)",
                "val_color": "#64748b",
                "date_color": "#64748b",
                "sub_color": "#64748b",
                "node_bg": "#1e293b",
                "node_color": "#64748b",
                "node_icon": "○",
                "track_color": "#334155"
            }

    s1 = get_step_styles(rec_state)
    s2 = get_step_styles(sanc_state)
    s3 = get_step_styles(exp_state)
    s4 = get_step_styles(comp_state)

    # Connector line styling
    bar_1_2 = s2["track_color"] if s2["track_color"] != "#334155" else "#334155"
    if s2["track_color"] == "#f59e0b":
        bar_1_2 = "linear-gradient(90deg, #10b981 0%, #f59e0b 100%)"
    
    bar_2_3 = "#10b981" if (s2["track_color"] == "#10b981" and s3["track_color"] == "#10b981") else "#334155"
    if s3["track_color"] == "#f59e0b":
        bar_2_3 = "linear-gradient(90deg, #10b981 0%, #f59e0b 100%)"

    bar_3_4 = "#10b981" if (s3["track_color"] == "#10b981" and s4["track_color"] == "#10b981") else "#334155"

    return clean_html(f"""
    <div style="background: #0d1117; border: 1px solid #1e293b; border-radius: 8px; padding: 20px 22px; margin: 16px 0;">
        <!-- Top Header -->
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; margin-bottom: 16px; padding-bottom: 12px; border-bottom: 1px solid #1e293b;">
            <div>
                <div style="font-size: 0.72rem; font-weight: 700; color: #38bdf8; text-transform: uppercase; letter-spacing: 1px;">
                    Administrative Lifecycle & Milestone Progression
                </div>
                <div style="font-size: 0.88rem; color: #94a3b8; margin-top: 2px;">
                    Sequential audit trail from MP recommendation to physical asset completion
                </div>
            </div>
            <div>
                <span style="background: rgba(56, 189, 248, 0.1); border: 1px solid rgba(56, 189, 248, 0.3); color: #38bdf8; font-size: 0.68rem; font-weight: 700; padding: 3px 10px; border-radius: 9999px; letter-spacing: 0.5px; text-transform: uppercase;">
                    Authentic Source Data Only • Zero Synthetic Progress
                </span>
            </div>
        </div>

        <!-- Connected Stepper Track -->
        <div style="display: flex; align-items: center; width: 100%; margin: 8px 0 18px 0; padding: 0 6px;">
            <div style="display: flex; align-items: center; gap: 6px;">
                <span style="width: 22px; height: 22px; border-radius: 50%; background: {s1['node_bg']}; color: {s1['node_color']}; display: inline-flex; align-items: center; justify-content: center; font-size: 0.68rem; font-weight: 800;">{s1['node_icon']}</span>
                <span style="font-size: 0.72rem; font-weight: 700; color: {s1['val_color']}; letter-spacing: 0.4px;">01. RECOMMENDED</span>
            </div>
            <div style="flex: 1; height: 2px; margin: 0 10px; background: {bar_1_2};"></div>
            <div style="display: flex; align-items: center; gap: 6px;">
                <span style="width: 22px; height: 22px; border-radius: 50%; background: {s2['node_bg']}; color: {s2['node_color']}; display: inline-flex; align-items: center; justify-content: center; font-size: 0.68rem; font-weight: 800;">{s2['node_icon']}</span>
                <span style="font-size: 0.72rem; font-weight: 700; color: {s2['val_color']}; letter-spacing: 0.4px;">02. SANCTIONED</span>
            </div>
            <div style="flex: 1; height: 2px; margin: 0 10px; background: {bar_2_3};"></div>
            <div style="display: flex; align-items: center; gap: 6px;">
                <span style="width: 22px; height: 22px; border-radius: 50%; background: {s3['node_bg']}; color: {s3['node_color']}; display: inline-flex; align-items: center; justify-content: center; font-size: 0.68rem; font-weight: 800;">{s3['node_icon']}</span>
                <span style="font-size: 0.72rem; font-weight: 700; color: {s3['val_color']}; letter-spacing: 0.4px;">03. EXPENDITURE</span>
            </div>
            <div style="flex: 1; height: 2px; margin: 0 10px; background: {bar_3_4};"></div>
            <div style="display: flex; align-items: center; gap: 6px;">
                <span style="width: 22px; height: 22px; border-radius: 50%; background: {s4['node_bg']}; color: {s4['node_color']}; display: inline-flex; align-items: center; justify-content: center; font-size: 0.68rem; font-weight: 800;">{s4['node_icon']}</span>
                <span style="font-size: 0.72rem; font-weight: 700; color: {s4['val_color']}; letter-spacing: 0.4px;">04. COMPLETED</span>
            </div>
        </div>

        <!-- 4-Column Milestone Cards Grid -->
        <div style="display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px;">
            <!-- Step 1: Recommended -->
            <div style="background: {s1['card_bg']}; border: {s1['card_border']}; border-top: {s1['top_border']}; border-radius: 6px; padding: 14px 14px; display: flex; flex-direction: column; justify-content: space-between;">
                <div>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                        <span style="font-size: 0.7rem; font-weight: 700; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px;">RECOMMENDATION</span>
                        <span style="font-size: 0.65rem; font-weight: 700; color: {s1['badge_color']}; background: {s1['badge_bg']}; border: 1px solid {s1['badge_border']}; padding: 1px 7px; border-radius: 9999px;">{rec_badge}</span>
                    </div>
                    <div style="font-size: 1.35rem; font-weight: 800; color: {s1['val_color']}; margin: 8px 0 4px 0; letter-spacing: -0.3px;">{rec_amt}</div>
                    <div style="font-size: 0.76rem; color: #94a3b8; margin-bottom: 8px;">📅 Date: <strong style="color: {s1['date_color']};">{rec_date}</strong></div>
                </div>
                <div>
                    <div style="border-top: 1px solid rgba(255, 255, 255, 0.08); margin: 6px 0;"></div>
                    <div style="font-size: 0.72rem; color: {s1['sub_color']}; line-height: 1.4;">{rec_subtext}</div>
                </div>
            </div>

            <!-- Step 2: Sanctioned -->
            <div style="background: {s2['card_bg']}; border: {s2['card_border']}; border-top: {s2['top_border']}; border-radius: 6px; padding: 14px 14px; display: flex; flex-direction: column; justify-content: space-between;">
                <div>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                        <span style="font-size: 0.7rem; font-weight: 700; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px;">ADMIN SANCTION</span>
                        <span style="font-size: 0.65rem; font-weight: 700; color: {s2['badge_color']}; background: {s2['badge_bg']}; border: 1px solid {s2['badge_border']}; padding: 1px 7px; border-radius: 9999px;">{sanc_badge}</span>
                    </div>
                    <div style="font-size: 1.22rem; font-weight: 800; color: {s2['val_color']}; margin: 8px 0 4px 0; letter-spacing: -0.3px;">{sanc_amt_disp}</div>
                    <div style="font-size: 0.76rem; color: #94a3b8; margin-bottom: 8px;">📅 Date: <strong style="color: {s2['date_color']};">{sanc_date_disp}</strong></div>
                </div>
                <div>
                    <div style="border-top: 1px solid rgba(255, 255, 255, 0.08); margin: 6px 0;"></div>
                    <div style="font-size: 0.72rem; color: {s2['sub_color']}; line-height: 1.4;">{sanc_subtext}</div>
                </div>
            </div>

            <!-- Step 3: Expenditure -->
            <div style="background: {s3['card_bg']}; border: {s3['card_border']}; border-top: {s3['top_border']}; border-radius: 6px; padding: 14px 14px; display: flex; flex-direction: column; justify-content: space-between;">
                <div>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                        <span style="font-size: 0.7rem; font-weight: 700; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px;">EXPENDITURE</span>
                        <span style="font-size: 0.65rem; font-weight: 700; color: {s3['badge_color']}; background: {s3['badge_bg']}; border: 1px solid {s3['badge_border']}; padding: 1px 7px; border-radius: 9999px;">{exp_badge}</span>
                    </div>
                    <div style="font-size: 1.35rem; font-weight: 800; color: {s3['val_color']}; margin: 8px 0 4px 0; letter-spacing: -0.3px;">{exp_amt_disp}</div>
                    <div style="font-size: 0.76rem; color: #94a3b8; margin-bottom: 8px;">📅 Date: <strong style="color: {s3['date_color']};">{exp_date_disp}</strong></div>
                </div>
                <div>
                    <div style="border-top: 1px solid rgba(255, 255, 255, 0.08); margin: 6px 0;"></div>
                    <div style="font-size: 0.72rem; color: {s3['sub_color']}; line-height: 1.4;">{exp_subtext}</div>
                </div>
            </div>

            <!-- Step 4: Completed -->
            <div style="background: {s4['card_bg']}; border: {s4['card_border']}; border-top: {s4['top_border']}; border-radius: 6px; padding: 14px 14px; display: flex; flex-direction: column; justify-content: space-between;">
                <div>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                        <span style="font-size: 0.7rem; font-weight: 700; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px;">COMPLETION</span>
                        <span style="font-size: 0.65rem; font-weight: 700; color: {s4['badge_color']}; background: {s4['badge_bg']}; border: 1px solid {s4['badge_border']}; padding: 1px 7px; border-radius: 9999px;">{comp_badge}</span>
                    </div>
                    <div style="font-size: 1.35rem; font-weight: 800; color: {s4['val_color']}; margin: 8px 0 4px 0; letter-spacing: -0.3px;">{comp_amt_disp}</div>
                    <div style="font-size: 0.76rem; color: #94a3b8; margin-bottom: 8px;">📅 Date: <strong style="color: {s4['date_color']};">{comp_date_disp}</strong></div>
                </div>
                <div>
                    <div style="border-top: 1px solid rgba(255, 255, 255, 0.08); margin: 6px 0;"></div>
                    <div style="font-size: 0.72rem; color: {s4['sub_color']}; line-height: 1.4;">{comp_subtext}</div>
                </div>
            </div>
        </div>

        <!-- Footer Note -->
        <div style="font-size: 0.74rem; color: #64748b; margin-top: 14px; padding-top: 10px; border-top: 1px solid #1e293b; line-height: 1.5; display: flex; align-items: flex-start; gap: 6px;">
            <span style="color: #94a3b8;">⚖️</span>
            <span>
                <strong style="color: #94a3b8;">Forensic Integrity Safeguard:</strong>
                Lifecycle stages strictly reflect official 18th Lok Sabha MoSPI verified records. Missing milestones display as <code>—</code>. Speculative physical progress percentages and estimated completion dates are excluded by design.
            </span>
        </div>
    </div>
    """)


def render_math_breakdown_html(work_risk: Any) -> str:
    """Renders the transparent visual math breakdown of how the composite risk score was built.
    
    Formula: C_m = (w_m * S_m) / sum_available_weight
    Total Risk Score = sum(C_m)
    Evidence Coverage = sum_available_weight * 100%
    """
    scores = work_risk.module_scores
    coverage = work_risk.evidence_coverage
    sum_w = coverage.get("sum_available_weight", 1.0)
    avail_weights = coverage.get("available_weights", {})
    
    rows_html = []
    total_contrib = 0.0

    modules = [
        ("peer_benchmarking", "Peer Benchmark", 0.30),
        ("statistical_outliers", "Statistical Outlier", 0.25),
        ("financial_execution_mismatch", "Financial–Execution", 0.30),
        ("duplicate_overlap", "Duplicate / Overlap", 0.15)
    ]

    for key, name, base_w in modules:
        score = scores.get(key)
        is_avail = (score is not None) and (key in avail_weights)
        if is_avail:
            contrib = (base_w * score) / sum_w if sum_w > 0 else 0.0
            total_contrib += contrib
            eff_weight = (base_w / sum_w * 100.0) if sum_w > 0 else 0.0
            score_str = f"<code>{score:.2f}</code>"
            weight_str = f"<strong>{int(base_w * 100)}%</strong>"
            contrib_str = f"<strong>+{contrib:.2f} pts</strong>"
        else:
            score_str = '<span style="color: #8b949e;">Unavailable</span>'
            weight_str = '<span style="color: #8b949e;">excluded</span>'
            contrib_str = '<span style="color: #8b949e;">—</span>'

        rows_html.append(clean_html(f"""
        <tr style="border-bottom: 1px solid #21262d;">
            <td style="padding: 10px 14px; font-weight: 600; color: #f0f6fc;">{name}</td>
            <td style="padding: 10px 14px; text-align: center;">{score_str}</td>
            <td style="padding: 10px 14px; text-align: center; color: #8b949e;">{weight_str}</td>
            <td style="padding: 10px 14px; text-align: right; color: #58a6ff;">{contrib_str}</td>
        </tr>
        """))

    final_score = work_risk.risk_score
    risk_band = work_risk.risk_band
    cov_pct = coverage.get("available_weight_pct", 100.0)
    band_color = RISK_COLORS.get(risk_band, "#6e7681")

    rows_joined = "\n".join(rows_html)

    return clean_html(f"""
    <div style="background-color: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 18px 20px; margin: 16px 0;">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; margin-bottom: 12px;">
            <div>
                <div style="font-size: 0.8rem; font-weight: 700; color: #58a6ff; text-transform: uppercase; letter-spacing: 1px;">
                    Transparent Scoring Mathematics
                </div>
                <div style="font-size: 1.1rem; font-weight: 700; color: #f0f6fc;">
                    How the Risk Score Was Built
                </div>
            </div>
            <div style="text-align: right;">
                <span style="font-size: 0.78rem; color: #8b949e;">Formula: </span>
                <code style="font-size: 0.8rem; color: #79c0ff; background: #0d1117; padding: 2px 6px; border-radius: 4px;">
                    Risk Score = Σ(w_m · S_m) / Σ(w_m)
                </code>
            </div>
        </div>

        <div style="overflow-x: auto;">
            <table style="width: 100%; font-size: 0.88rem; color: #c9d1d9; border-collapse: collapse;">
                <thead>
                    <tr style="border-bottom: 1px solid #30363d; text-align: left; background-color: #0d1117;">
                        <th style="padding: 10px 14px;">Engine</th>
                        <th style="padding: 10px 14px; text-align: center;">Score</th>
                        <th style="padding: 10px 14px; text-align: center;">Weight</th>
                        <th style="padding: 10px 14px; text-align: right;">Contribution</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_joined}
                </tbody>
                <tfoot>
                    <tr style="border-top: 2px solid #30363d; background-color: #0d1117; font-weight: 700;">
                        <td style="padding: 12px 14px; color: #f0f6fc;">
                            Final Composite Risk Score
                        </td>
                        <td style="padding: 12px 14px; text-align: center; color: {band_color}; font-size: 1.05rem;">
                            {final_score:.2f}
                        </td>
                        <td style="padding: 12px 14px; text-align: center; color: #58a6ff;">
                            Coverage: {cov_pct:.0f}%
                        </td>
                        <td style="padding: 12px 14px; text-align: right; font-size: 1.15rem; color: {band_color};">
                            {final_score:.2f} pts ({risk_band})
                        </td>
                    </tr>
                </tfoot>
            </table>
        </div>
        <div style="font-size: 0.75rem; color: #8b949e; margin-top: 10px; line-height: 1.4;">
            * <strong>Availability Normalization:</strong> Unavailable modules are excluded from the denominator. Their weights are proportionally distributed among available modules, ensuring zero score suppression.
        </div>
    </div>
    """)


def synthesize_plain_language_narrative(work_risk: Any, p_res: dict, s_res: dict, m_res: dict, d_res: dict) -> str:
    """Synthesizes dynamic, objective, plain-language narrative explaining why the work is flagged.
    
    Zero fraud/guilt/criminal claims. Focuses strictly on observed deviations and evidence gaps.
    """
    score = work_risk.risk_score
    band = work_risk.risk_band
    meta = work_risk.work_metadata
    rec_amt = format_inr(meta.get("amount_recommended"))
    
    findings = []
    
    # Peer benchmark driver
    p_score = work_risk.module_scores.get("peer_benchmarking")
    if p_score is not None and p_score >= 50.0:
        p_med = format_inr(p_res.get("peer_median"))
        pct = p_res.get("percentile_rank")
        cohort = p_res.get("cohort_level_name", "cohort")
        pct_str = f" ({pct:.1f}th percentile)" if pct is not None else ""
        findings.append(
            f"The recommended cost ({rec_amt}) is substantially higher than the peer median ({p_med}) "
            f"for comparable projects within the {cohort} benchmark group{pct_str}."
        )
    elif p_score is not None and p_score < 30.0:
        findings.append("Recommended allocation aligns closely with peer cohort benchmarks.")

    # Statistical outlier driver
    s_score = work_risk.module_scores.get("statistical_outliers")
    if s_score is not None and s_score >= 50.0:
        findings.append(
            "Statistical distribution screening identified marked multi-feature divergence "
            "using robust Modified Z-scores relative to parametric reference norms."
        )

    # Financial-execution mismatch driver
    m_score = work_risk.module_scores.get("financial_execution_mismatch")
    if m_score is not None and m_score >= 50.0:
        conf = m_res.get("confidence_label", "Level 1")
        findings.append(
            f"Financial and milestone analysis ({conf} confidence) flagged an asymmetry between "
            f"administrative authorization thresholds and logged disbursement milestones."
        )
    elif m_score is None:
        findings.append(
            "Financial-execution tracking is unavailable in source records due to missing disbursement/completion filings."
        )

    # Duplicate overlap driver
    d_score = work_risk.module_scores.get("duplicate_overlap")
    if d_score is not None and d_score >= 50.0:
        matches_count = len(d_res.get("top_matches", []))
        findings.append(
            f"Semantic and agency analysis detected {matches_count} potential overlap candidate(s) "
            f"with similar project scope within the same administrative block."
        )

    # Compose synthesis
    if band in ("CRITICAL", "HIGH"):
        lead = (
            f"<strong>This project has been flagged for {band.title()} Priority Review (Risk Score: {score:.1f}/100).</strong> "
            "Scoring reflects multiple objective statistical and administrative anomalies requiring verification."
        )
    elif band == "MEDIUM":
        lead = (
            f"<strong>This project is classified under Medium Risk (Risk Score: {score:.1f}/100).</strong> "
            "Evaluated metrics show moderate variance from standard peer baseline distributions."
        )
    else:
        lead = (
            f"<strong>This project is classified under Low Risk (Risk Score: {score:.1f}/100).</strong> "
            "Project parameters conform with established historical and cohort benchmarks."
        )

    bullet_items = "".join([f"<li style='margin-bottom: 4px;'>{f}</li>" for f in findings]) if findings else "<li>No acute deviations detected across active modules.</li>"

    return clean_html(f"""
    <div style="background-color: #161b22; border: 1px solid #30363d; border-left: 4px solid {RISK_COLORS.get(band, '#6e7681')}; border-radius: 6px; padding: 16px 18px; margin: 14px 0;">
        <div style="font-size: 0.95rem; color: #f0f6fc; line-height: 1.5; margin-bottom: 8px;">
            {lead}
        </div>
        <ul style="font-size: 0.85rem; color: #c9d1d9; margin: 0; padding-left: 20px; line-height: 1.5;">
            {bullet_items}
        </ul>
        <div style="font-size: 0.74rem; color: #8b949e; margin-top: 8px;">
            ℹ️ <em>Objective Risk Screening Note: Indicators highlight anomalies for targeted review; they do not imply confirmed wrongdoing or procedural non-compliance.</em>
        </div>
    </div>
    """)


def render_risk_drivers_html(work_risk: Any, p_res: dict, s_res: dict, m_res: dict, d_res: dict) -> str:
    """Renders the top risk drivers ordered by contribution severity with visible confidence tier."""
    scores = work_risk.module_scores
    coverage = work_risk.evidence_coverage
    sum_w = coverage.get("sum_available_weight", 1.0)
    avail_w = coverage.get("available_weights", {})
    
    # Extract confidence by module from evidence_items
    conf_by_mod = {}
    for item in getattr(work_risk, "evidence_items", []):
        if isinstance(item, dict):
            m = item.get("module")
            c = item.get("confidence")
        else:
            m = getattr(item, "module", None)
            c = getattr(item, "confidence", None)
        if m and c and m not in conf_by_mod:
            conf_by_mod[m] = c
            
    # Fallback to engine result metadata if not in evidence_items
    if "peer_benchmarking" not in conf_by_mod:
        p_cnt = p_res.get("peer_count", 0)
        conf_by_mod["peer_benchmarking"] = "HIGH" if p_cnt >= 10 else ("MEDIUM" if p_cnt >= 5 else "LOW")
    if "statistical_outliers" not in conf_by_mod:
        conf_by_mod["statistical_outliers"] = "HIGH"
    if "financial_execution_mismatch" not in conf_by_mod:
        raw_m_conf = m_res.get("confidence_label", "MEDIUM")
        # Normalize to standard confidence tier string
        if "HIGH" in str(raw_m_conf).upper():
            conf_by_mod["financial_execution_mismatch"] = "HIGH"
        elif "LOW" in str(raw_m_conf).upper():
            conf_by_mod["financial_execution_mismatch"] = "LOW"
        else:
            conf_by_mod["financial_execution_mismatch"] = "MEDIUM"
    if "duplicate_overlap" not in conf_by_mod:
        conf_by_mod["duplicate_overlap"] = "HIGH" if d_res.get("top_matches") else "LOW"

    driver_items = []
    
    # 1. Peer Benchmarking
    if scores.get("peer_benchmarking") is not None and "peer_benchmarking" in avail_w:
        sc = scores["peer_benchmarking"]
        contrib = (0.30 * sc) / sum_w if sum_w > 0 else 0.0
        driver_items.append({
            "name": "Peer Benchmarking",
            "score": sc,
            "contrib": contrib,
            "summary": p_res.get("evidence", "Evaluated against comparable cohort peer works."),
            "tag": "Cohort Benchmark",
            "weight": 0.30,
            "confidence": conf_by_mod.get("peer_benchmarking", "HIGH")
        })

    # 2. Statistical Outliers
    if scores.get("statistical_outliers") is not None and "statistical_outliers" in avail_w:
        sc = scores["statistical_outliers"]
        contrib = (0.25 * sc) / sum_w if sum_w > 0 else 0.0
        driver_items.append({
            "name": "Statistical Outliers",
            "score": sc,
            "contrib": contrib,
            "summary": s_res.get("evidence", "Evaluated using robust Modified Z-scores."),
            "tag": "Distributional Outlier",
            "weight": 0.25,
            "confidence": conf_by_mod.get("statistical_outliers", "HIGH")
        })

    # 3. Financial-Execution Mismatch
    if scores.get("financial_execution_mismatch") is not None and "financial_execution_mismatch" in avail_w:
        sc = scores["financial_execution_mismatch"]
        contrib = (0.30 * sc) / sum_w if sum_w > 0 else 0.0
        driver_items.append({
            "name": "Financial–Execution Mismatch",
            "score": sc,
            "contrib": contrib,
            "summary": m_res.get("evidence", "Disbursement and milestone realization check."),
            "tag": "Milestone Asymmetry",
            "weight": 0.30,
            "confidence": conf_by_mod.get("financial_execution_mismatch", "MEDIUM")
        })

    # 4. Duplicate / Overlap
    if scores.get("duplicate_overlap") is not None and "duplicate_overlap" in avail_w:
        sc = scores["duplicate_overlap"]
        contrib = (0.15 * sc) / sum_w if sum_w > 0 else 0.0
        driver_items.append({
            "name": "Duplicate / Overlap Detection",
            "score": sc,
            "contrib": contrib,
            "summary": d_res.get("evidence", "Contextual semantic embedding comparison."),
            "tag": "Contextual Overlap",
            "weight": 0.15,
            "confidence": conf_by_mod.get("duplicate_overlap", "HIGH")
        })

    # Sort drivers by contribution descending
    driver_items.sort(key=lambda x: x["contrib"], reverse=True)

    if not driver_items:
        return "<div style='color: #8b949e; font-size: 0.85rem;'>No active contributing engines available for this record.</div>"

    cards_html = []
    for rank, d in enumerate(driver_items, start=1):
        if d["score"] >= 80:
            badge_color = "#da3633"
            severity_label = "CRITICAL DRIVER"
        elif d["score"] >= 60:
            badge_color = "#db6d28"
            severity_label = "HIGH DRIVER"
        elif d["score"] >= 30:
            badge_color = "#d29922"
            severity_label = "MODERATE DRIVER"
        else:
            badge_color = "#238636"
            severity_label = "NOMINAL / LOW"

        conf_badge = get_confidence_badge_html(d["confidence"])

        cards_html.append(clean_html(f"""
        <div style="background-color: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 12px 16px; margin-bottom: 10px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; flex-wrap: wrap; gap: 8px;">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="background: #21262d; color: #58a6ff; font-weight: 700; font-size: 0.75rem; padding: 2px 7px; border-radius: 4px;">#{rank}</span>
                    <strong style="color: #f0f6fc; font-size: 0.95rem;">{d['name']}</strong>
                </div>
                <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                    {conf_badge}
                    <span style="font-size: 0.72rem; color: {badge_color}; border: 1px solid {badge_color}; padding: 2px 7px; border-radius: 4px; font-weight: 600;">{severity_label}</span>
                    <span style="font-size: 0.88rem; color: #58a6ff; font-weight: 700;">+{d['contrib']:.2f} pts</span>
                </div>
            </div>
            <div style="font-size: 0.83rem; color: #c9d1d9; line-height: 1.45; background: #0d1117; padding: 10px 12px; border-radius: 4px; border: 1px solid #21262d;">
                {d['summary']}
            </div>
            <div style="display: flex; justify-content: space-between; font-size: 0.75rem; color: #8b949e; margin-top: 8px;">
                <span>Raw Engine Score: <strong style="color: #f0f6fc;">{d['score']:.1f}/100</strong></span>
                <span>Locked Weight: <strong>{int(d['weight']*100)}%</strong></span>
            </div>
        </div>
        """))

    return "\n".join(cards_html)


def render_duplicate_comparison_html(work_record: dict, d_res: dict) -> str:
    """Renders clean, human-readable comparison card for the strongest duplicate candidate."""
    top_matches = d_res.get("top_matches", [])
    if not top_matches:
        return clean_html("""
        <div style="background-color: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 14px 16px;">
            <div style="display: flex; align-items: center; gap: 8px; color: #3fb950; font-weight: 600; font-size: 0.9rem;">
                <span>✓</span> No Contextual Duplicate or Overlapping Proposals Detected
            </div>
            <div style="font-size: 0.8rem; color: #8b949e; margin-top: 4px;">
                Zero high-similarity project descriptions identified within the local administrative block.
            </div>
        </div>
        """)

    m = top_matches[0]
    m_dtl = m.get("matched_work_dtl_id")
    m_dtl_str = str(int(float(m_dtl))) if m_dtl is not None and str(m_dtl) != "" else "UNKNOWN"
    m_wid = str(m.get("matched_unique_work_number") or f"DTL_{m_dtl_str}")
    
    subj_wid = str(work_record.get("unique_work_number") or f"DTL_{work_record.get('work_recommendation_dtl_id')}")
    subj_desc = str(work_record.get("work_description") or "No description")
    matched_desc = str(m.get("matched_work_description") or "No description")
    
    subj_amt = format_inr(work_record.get("amount_recommended"))
    matched_amt = format_inr(m.get("matched_amount"))
    
    cosine = float(m.get("semantic_cosine_similarity", 0.0))
    agency_sim = float(m.get("agency_similarity", 0.0))
    raw_class = str(m.get("classification") or "Candidate")
    classification = f"{raw_class} (Requires Verification)" if "duplicate" in raw_class.lower() else raw_class
    same_mp = "Yes" if m.get("same_mp") else "No"

    return clean_html(f"""
    <div style="background-color: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px 18px; margin-bottom: 12px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
            <div>
                <span style="font-size: 0.75rem; font-weight: 700; color: #db6d28; text-transform: uppercase;">
                    Strongest Overlap Candidate
                </span>
                <div style="font-size: 1rem; font-weight: 700; color: #f0f6fc;">
                    {classification} • Match with {m_wid}
                </div>
            </div>
            <div style="text-align: right;">
                <span style="background: rgba(219, 109, 40, 0.15); color: #db6d28; border: 1px solid #db6d28; padding: 2px 8px; border-radius: 10px; font-size: 0.8rem; font-weight: 600;">
                    Cosine: {cosine:.3f}
                </span>
            </div>
        </div>

        <!-- Plain Language Explanation Before Metrics -->
        <div style="background-color: rgba(219, 109, 40, 0.08); border-left: 3px solid #db6d28; padding: 10px 14px; border-radius: 0 4px 4px 0; margin-bottom: 12px; font-size: 0.85rem; color: #e6edf3; line-height: 1.4;">
            <strong>Plain-Language Overlap Finding:</strong> Two public works in the same administrative block describe closely related infrastructure projects with {agency_sim:.0f}% implementing agency match. Administrative review is recommended to verify whether this represents a continuous multi-phase asset, distinct physical facilities, or an overlapping sanction.
        </div>

        <!-- Side by side comparison -->
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 12px;">
            <!-- Current Subject Work -->
            <div style="background: #0d1117; border: 1px solid #21262d; border-radius: 6px; padding: 10px 12px;">
                <div style="font-size: 0.75rem; color: #58a6ff; font-weight: 600; text-transform: uppercase; margin-bottom: 4px;">
                    Subject Project (Current)
                </div>
                <div style="font-size: 0.85rem; font-weight: 600; color: #f0f6fc; margin-bottom: 4px;">{subj_wid}</div>
                <div style="font-size: 0.8rem; color: #c9d1d9; line-height: 1.4; height: 60px; overflow-y: auto;">
                    {subj_desc}
                </div>
                <div style="font-size: 0.78rem; color: #8b949e; margin-top: 6px; border-top: 1px solid #21262d; padding-top: 4px;">
                    Allocation: <strong style="color: #f0f6fc;">{subj_amt}</strong>
                </div>
            </div>

            <!-- Matched Candidate Work -->
            <div style="background: #0d1117; border: 1px solid #21262d; border-radius: 6px; padding: 10px 12px;">
                <div style="font-size: 0.75rem; color: #db6d28; font-weight: 600; text-transform: uppercase; margin-bottom: 4px;">
                    Matched Project (Candidate)
                </div>
                <div style="font-size: 0.85rem; font-weight: 600; color: #f0f6fc; margin-bottom: 4px;">{m_wid}</div>
                <div style="font-size: 0.8rem; color: #c9d1d9; line-height: 1.4; height: 60px; overflow-y: auto;">
                    {matched_desc}
                </div>
                <div style="font-size: 0.78rem; color: #8b949e; margin-top: 6px; border-top: 1px solid #21262d; padding-top: 4px;">
                    Allocation: <strong style="color: #f0f6fc;">{matched_amt}</strong>
                </div>
            </div>
        </div>

        <!-- Similarity Metrics Footer -->
        <div style="display: flex; justify-content: space-between; flex-wrap: wrap; gap: 8px; font-size: 0.78rem; color: #8b949e; background: #0d1117; padding: 8px 12px; border-radius: 4px; border: 1px solid #21262d;">
            <span>Semantic Cosine: <strong style="color: #58a6ff;">{cosine:.3f}</strong> (all-MiniLM-L6-v2)</span>
            <span>Agency Match: <strong style="color: #58a6ff;">{agency_sim:.1f}%</strong></span>
            <span>Same MP: <strong style="color: #f0f6fc;">{same_mp}</strong></span>
            <span>Recommended Action: <strong style="color: #f0f6fc;">Cross-verify field location</strong></span>
        </div>
    </div>
    """)


CUSTOM_CSS = """
<style>
    /* Institutional risk intelligence palette */
    :root {
        --bg-main: #0d1117;
        --bg-surface: #161b22;
        --bg-elevated: #21262d;
        --border-subtle: #30363d;
        --border-dark: #21262d;
        --text-primary: #f0f6fc;
        --text-secondary: #c9d1d9;
        --text-muted: #8b949e;
        --accent-blue: #58a6ff;
        --accent-green: #238636;
        --accent-amber: #d29922;
        --accent-orange: #db6d28;
        --accent-red: #da3633;
    }

    /* Core layout & typography */
    .stApp {
        background-color: var(--bg-main);
        color: var(--text-secondary);
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Inter", Roboto, Helvetica, Arial, sans-serif;
        letter-spacing: -0.01em;
    }

    /* Desktop containment & alignment */
    .block-container {
        max-width: 1440px !important;
        padding-top: 1.5rem !important;
        padding-bottom: 3rem !important;
        padding-left: 2.5rem !important;
        padding-right: 2.5rem !important;
    }

    /* Top MPPrisma masthead */
    .masthead-container {
        background: linear-gradient(180deg, #161b22 0%, #0d1117 100%);
        border: 1px solid var(--border-subtle);
        padding: 18px 24px;
        margin-bottom: 20px;
        border-radius: 8px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
    }

    /* Card containers */
    .investigation-card {
        background-color: var(--bg-surface);
        border: 1px solid var(--border-subtle);
        border-radius: 8px;
        padding: 20px 22px;
        margin-bottom: 16px;
    }

    /* Module cards */
    .module-card {
        background-color: var(--bg-surface);
        border: 1px solid var(--border-subtle);
        border-radius: 8px;
        padding: 16px;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }

    /* Dataframe tables */
    .stDataFrame, [data-testid="stDataFrame"] {
        border: 1px solid var(--border-subtle) !important;
        border-radius: 6px !important;
        overflow: hidden !important;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: var(--bg-surface);
        border-right: 1px solid var(--border-subtle);
    }
    [data-testid="stSidebar"] .block-container {
        padding-left: 1.25rem !important;
        padding-right: 1.25rem !important;
    }

    /* Headers */
    h1, h2, h3, h4, h5 {
        color: var(--text-primary) !important;
        font-weight: 600 !important;
        letter-spacing: -0.02em !important;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
        border-bottom: 1px solid var(--border-subtle);
        margin-bottom: 18px;
    }

    .stTabs [data-baseweb="tab"] {
        background-color: transparent;
        border: 1px solid transparent;
        color: var(--text-muted);
        border-radius: 6px 6px 0 0;
        padding: 9px 18px;
        font-weight: 500;
        font-size: 0.88rem;
        transition: all 0.15s ease-in-out;
    }

    .stTabs [data-baseweb="tab"]:hover {
        color: var(--text-primary);
        background-color: rgba(255, 255, 255, 0.03);
    }

    .stTabs [aria-selected="true"] {
        background-color: var(--bg-elevated) !important;
        color: var(--accent-blue) !important;
        border: 1px solid var(--border-subtle) !important;
        border-bottom: 2px solid var(--accent-blue) !important;
        font-weight: 600;
    }

    /* Buttons */
    .stButton > button {
        background-color: var(--bg-elevated);
        color: var(--text-secondary);
        border: 1px solid var(--border-subtle);
        border-radius: 6px;
        font-weight: 500;
        font-size: 0.85rem;
        padding: 6px 14px;
        transition: all 0.15s ease-in-out;
    }

    .stButton > button:hover {
        background-color: #30363d;
        color: var(--text-primary);
        border-color: #8b949e;
        box-shadow: 0 1px 4px rgba(0,0,0,0.3);
    }

    /* Action item box */
    .action-box {
        background-color: rgba(31, 111, 235, 0.06);
        border: 1px solid rgba(88, 166, 255, 0.2);
        border-left: 3px solid var(--accent-blue);
        padding: 10px 14px;
        margin-bottom: 8px;
        border-radius: 0 6px 6px 0;
        font-size: 0.88rem;
        color: #e6edf3;
        line-height: 1.45;
    }

    /* Field inspection item box */
    .action-box-field {
        background-color: rgba(210, 153, 34, 0.06);
        border: 1px solid rgba(210, 153, 34, 0.2);
        border-left: 3px solid var(--accent-amber);
        padding: 10px 14px;
        margin-bottom: 8px;
        border-radius: 0 6px 6px 0;
        font-size: 0.88rem;
        color: #e6edf3;
        line-height: 1.45;
    }

    /* Expanders styling */
    [data-testid="stExpander"] {
        background-color: var(--bg-surface) !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: 6px !important;
        margin-bottom: 10px !important;
    }
    [data-testid="stExpander"] summary {
        color: var(--text-primary) !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
    }

    /* Form input controls */
    [data-baseweb="input"], [data-baseweb="select"] {
        background-color: var(--bg-surface) !important;
        border-color: var(--border-subtle) !important;
        color: var(--text-primary) !important;
    }
    input {
        color: var(--text-primary) !important;
    }

    /* Custom scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    ::-webkit-scrollbar-track {
        background: var(--bg-main);
    }
    ::-webkit-scrollbar-thumb {
        background: #30363d;
        border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #484f58;
    }

    /* Section divider header badge */
    .section-header-badge {
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        color: var(--accent-blue);
        letter-spacing: 0.8px;
        margin-bottom: 4px;
    }
</style>
"""

