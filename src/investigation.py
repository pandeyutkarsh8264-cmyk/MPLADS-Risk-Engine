"""Investigation Actions Generator.

Generates concrete next-step checks and verification actions based on observed evidence.
Adheres strictly to the specification:
- Uses objective, investigator-facing language (“Review sanction / implementation timeline / completion evidence”)
- NEVER claims fraud or guilt
- Directs investigators to primary source records, vouchers, and field verifications
"""

from typing import Dict, Any, List, Set


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
