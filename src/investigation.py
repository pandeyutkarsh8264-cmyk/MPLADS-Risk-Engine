"""Investigation Actions Generator.

Generates concrete next-step checks and verification actions based on observed evidence.
Adheres strictly to the specification:
- Uses objective, investigator-facing language (“Review sanction / implementation timeline / completion evidence”)
- NEVER claims fraud or guilt
- Directs investigators to primary source records, vouchers, and field verifications
"""

from typing import Dict, Any, List, Set, Optional


def generate_investigation_actions(
    risk_score: float,
    risk_band: str,
    module_scores: Dict[str, Any],
    all_reason_codes: List[str],
    evidence_items: List[Dict[str, Any]],
    work: Dict[str, Any]
) -> List[str]:
    """Generates concrete, evidence-driven next steps for field and desk review."""
    actions: List[str] = []
    codes_set: Set[str] = set(all_reason_codes)

    # 1. Peer benchmarking actions
    peer_score = module_scores.get("peer_benchmarking") or 0.0
    if peer_score >= 60.0 or any("PEER_OUTLIER" in c or "PEER_EXTREME" in c for c in codes_set):
        actions.append(
            "Review detailed project estimate and technical sanction to verify basis for recommended cost exceeding peer cohort norm."
        )
        actions.append(
            f"Inspect comparable works in {work.get('district', 'the district')} to assess whether site-specific terrain or scope justified higher allocation."
        )

    # 2. Statistical feature actions
    stat_score = module_scores.get("statistical_outliers") or 0.0
    if stat_score >= 50.0 or any("STAT_OUTLIER" in c or "STAT_EXTREME" in c for c in codes_set):
        actions.append(
            "Audit sanction delay documentation to identify potential administrative or inter-departmental clearance bottlenecks."
        )
        actions.append(
            "Verify ratio of sanctioned to recommended cost against standard departmental schedule of rates (SoR)."
        )

    # 3. Financial-execution mismatch actions
    mismatch_score = module_scores.get("financial_execution_mismatch") or 0.0
    if any("COST_OVERRUN" in c for c in codes_set):
        actions.append(
            "Review final measurement book (MB) and completion certificate to verify whether cost overrun received formal administrative approval."
        )

    if any("DISBURSEMENT_EXCEEDS_SANCTION" in c for c in codes_set):
        actions.append(
            "Reconcile vendor payment vouchers and bank disbursement statements against the approved work sanction limit."
        )

    if any("IMPOSSIBLY_FAST_COMPLETION" in c for c in codes_set):
        actions.append(
            "Inspect site handover records and engineer sign-off dates to verify realistic physical implementation duration."
        )

    if any("STALLED_EXECUTION" in c for c in codes_set):
        actions.append(
            "Issue formal inquiry to implementing agency regarding project stalling and status of committed fund allocation."
        )

    # 4. Duplicate / overlap actions
    dup_score = module_scores.get("duplicate_overlap") or 0.0
    if any("DUPLICATE_LIKELY" in c for c in codes_set):
        # Find matched work IDs from evidence items
        matched_ids = []
        for it in evidence_items:
            if it.get("module") == "duplicate_overlap" and "DTL_" in it.get("metric", ""):
                matched_ids.append(it["metric"].split("DTL_")[-1])

        match_ref = f" (matched DTL ID(s): {', '.join(matched_ids[:2])})" if matched_ids else ""
        actions.append(
            f"Verify physical site and cross-reference work description{match_ref} to confirm distinct asset creation."
        )
        actions.append(
            "Verify geographic boundary markers and landmark demarcation with local panchayat / municipal authority."
        )
    elif any("DUPLICATE_POSSIBLE" in c for c in codes_set):
        actions.append(
            "Review scope of work and Bill of Quantities (BoQ) for potential functional overlap with adjacent projects in the same sector."
        )

    # 5. Default action if no specific flags
    if not actions:
        if risk_band == "LOW":
            actions.append(
                "Standard routine monitoring; all statutory milestones and cost benchmarks align with historical norms."
            )
        else:
            actions.append(
                "Conduct periodic desk audit of implementation progress and expenditure vouchers upon next quarterly return."
            )

    return actions


def generate_deterministic_next_checks(
    work_risk: Any,
    work_record: Dict[str, Any],
    p_res: Optional[Dict[str, Any]] = None,
    s_res: Optional[Dict[str, Any]] = None,
    m_res: Optional[Dict[str, Any]] = None,
    d_res: Optional[Dict[str, Any]] = None
) -> List[Dict[str, str]]:
    """Generates deterministic, evidence-driven investigator directives.
    
    Adheres strictly to objective audit standards and neutral phrasing.
    Never asserts fraud, corruption, or guilt.
    """
    directives: List[Dict[str, str]] = []

    # Retrieve available metrics safely
    risk_score = float(getattr(work_risk, "risk_score", 0.0) or 0.0) if work_risk else 0.0
    risk_band = getattr(work_risk, "risk_band", "LOW") if work_risk else "LOW"
    
    cov_dict = getattr(work_risk, "evidence_coverage", {}) if work_risk else {}
    if isinstance(cov_dict, dict):
        avail_weight = float(cov_dict.get("available_weight_pct", 100.0) or 100.0)
    else:
        avail_weight = float(getattr(cov_dict, "available_weight_pct", 100.0) or 100.0)

    p_score = p_res.get("score") if p_res else None
    s_score = s_res.get("score") if s_res else None
    m_score = m_res.get("score") if m_res else None
    d_score = d_res.get("score") if d_res else None

    # Check 1: Missing Evidence / Low Coverage
    if avail_weight < 60.0:
        directives.append({
            "category": "Evidence Completeness",
            "priority": "HIGH",
            "action": "Obtain the missing supporting documentation before concluding the case.",
            "rationale": f"Current evidence coverage is {avail_weight:.0f}% (below 60% threshold). Key milestone records are absent."
        })
    elif avail_weight < 85.0:
        directives.append({
            "category": "Evidence Completeness",
            "priority": "MEDIUM",
            "action": "Collect the missing evidence before relying on this risk assessment.",
            "rationale": f"Partial evidence availability ({avail_weight:.0f}% observed weight). Desk review requires additional vouchers."
        })

    # Check 2: Statistical & Peer Anomaly
    if (s_score is not None and s_score >= 60.0) or (p_score is not None and p_score >= 60.0):
        directives.append({
            "category": "Peer & Cost Benchmarking",
            "priority": "HIGH" if max(s_score or 0, p_score or 0) >= 75 else "MEDIUM",
            "action": "Review the project's financial and execution values against comparable works.",
            "rationale": f"High statistical outlier score ({s_score or 0:.1f}) or elevated peer cohort percentile ({p_score or 0:.1f})."
        })

    # Check 3: Financial–Execution Mismatch
    if m_score is not None and m_score >= 40.0:
        directives.append({
            "category": "Financial–Execution Verification",
            "priority": "HIGH" if m_score >= 60.0 else "MEDIUM",
            "action": "Verify the underlying financial and execution records for consistency.",
            "rationale": f"Milestone timing or disbursement variance detected with mismatch score of {m_score:.1f}."
        })

    # Check 4: Semantic Overlap / Scope Comparison
    if d_score is not None and d_score > 0:
        top_cand = d_res.get("top_matches", [{}])[0] if d_res else {}
        cand_id = top_cand.get("matched_work_dtl_id", "adjacent project")
        directives.append({
            "category": "Scope & Overlap Audit",
            "priority": "HIGH",
            "action": "Compare project scope, implementing agency and administrative context.",
            "rationale": f"High text and context similarity surfaced against candidate DTL {cand_id}."
        })

    # Check 5: Baseline Verification (if no critical flags)
    if not directives:
        directives.append({
            "category": "Routine Quality Audit",
            "priority": "LOW",
            "action": "Review supporting records and confirm that project details are internally consistent.",
            "rationale": "Project milestones and cost benchmarks conform within normal statistical boundaries."
        })

    return directives
