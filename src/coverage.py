"""Coverage and Data Availability Assessment Module.

Calculates:
- Module availability before fusion
- Percentage of locked module weight actually available
- Explicit distinction between observed vs proxy evidence
- Level 3 physical progress tracking (strictly unavailable)
- Never converts missing evidence or expenditure into zero
"""

from typing import Dict, Any, List, Optional

LOCKED_WEIGHTS = {
    "peer_benchmarking": 0.30,
    "statistical_outliers": 0.25,
    "financial_execution_mismatch": 0.30,
    "duplicate_overlap": 0.15,
}


def calculate_evidence_coverage(
    module_scores: Dict[str, Optional[float]],
    work: Dict[str, Any],
    mismatch_eval: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Evaluates data and module coverage for a work prior to fusion.

    Returns:
      dict with:
        available_weight_pct: float (0.0 to 100.0)
        modules_available: list of available module keys
        modules_missing: list of missing/unavailable module keys
        available_weights: dict of weights for available modules
        observed_vs_proxy: str ("fully_observed", "partially_proxy", "proxy_only", "insufficient")
        has_completion_evidence: bool
        has_expenditure_evidence: bool
        level_3_physical_progress_available: bool (always False)
    """
    modules_available = []
    modules_missing = []
    available_weights = {}
    sum_available_weight = 0.0

    for mod, weight in LOCKED_WEIGHTS.items():
        score = module_scores.get(mod)
        if score is not None:
            modules_available.append(mod)
            available_weights[mod] = weight
            sum_available_weight += weight
        else:
            modules_missing.append(mod)

    available_weight_pct = round((sum_available_weight / sum(LOCKED_WEIGHTS.values())) * 100.0, 2)

    import math
    def _is_valid_num(val):
        if val is None:
            return False
        try:
            f = float(val)
            return not math.isnan(f)
        except (ValueError, TypeError):
            return False

    has_comp = bool(work.get("has_completion_evidence", False) or _is_valid_num(work.get("amount_completed")))
    has_exp = bool(work.get("has_expenditure_evidence", False) or _is_valid_num(work.get("total_disbursed_amount")))

    # Determine observed vs proxy evidence status
    if has_comp and has_exp:
        obs_status = "fully_observed"
    elif has_comp or has_exp:
        obs_status = "partially_proxy"
    elif len(modules_available) >= 2:
        obs_status = "proxy_only"
    else:
        obs_status = "insufficient"

    # Mismatch confidence detail
    mismatch_conf = mismatch_eval.get("confidence_label", "LOW") if mismatch_eval else "NONE"

    return {
        "available_weight_pct": available_weight_pct,
        "modules_available": modules_available,
        "modules_missing": modules_missing,
        "available_weights": available_weights,
        "sum_available_weight": round(sum_available_weight, 4),
        "observed_vs_proxy": obs_status,
        "has_completion_evidence": has_comp,
        "has_expenditure_evidence": has_exp,
        "mismatch_confidence_tier": mismatch_conf,
        "level_3_physical_progress_available": False,
        "physical_progress_status": "UNAVAILABLE_IN_SOURCE"
    }
