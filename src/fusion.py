"""Availability-Normalized Evidence Fusion and WorkRisk Generator.

Implements:
1. Locked Availability-Normalized Weighted Fusion:
   - Peer Benchmarking: 0.30
   - Statistical Outliers: 0.25
   - Financial–Execution Mismatch: 0.30
   - Duplicate/Overlap: 0.15
   - Missing modules are strictly excluded from the denominator (never treated as zero).
   - Risk score clamped to [0.0, 100.0].
2. Locked Risk Bands:
   - 0–29 = LOW
   - 30–59 = MEDIUM
   - 60–79 = HIGH
   - 80–100 = CRITICAL
3. Final WorkRisk Object generation with full evidence traceability and concrete investigation actions.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

from src.coverage import calculate_evidence_coverage, LOCKED_WEIGHTS
from src.evidence import (
    build_peer_evidence,
    build_stat_evidence,
    build_mismatch_evidence,
    build_duplicate_evidence,
    EvidenceItem
)
from src.investigation import generate_investigation_actions


@dataclass
class WorkRisk:
    work_id: str
    risk_score: Optional[float]
    risk_band: str
    evidence_coverage: Dict[str, Any]
    module_scores: Dict[str, Optional[float]]
    evidence_items: List[Dict[str, Any]]
    investigation_actions: List[str]
    work_metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def determine_risk_band(score: Optional[float]) -> str:
    """Assigns risk band per locked cutoffs: 0-29 LOW, 30-59 MEDIUM, 60-79 HIGH, 80-100 CRITICAL."""
    if score is None:
        return "UNAVAILABLE"
    # Clamp for robust evaluation
    s = min(100.0, max(0.0, score))
    if s < 30.0:
        return "LOW"
    elif s < 60.0:
        return "MEDIUM"
    elif s < 80.0:
        return "HIGH"
    else:
        return "CRITICAL"


class RiskFusionEngine:
    """Combines independent engine outputs into an availability-normalized composite risk score."""

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.weights = weights or dict(LOCKED_WEIGHTS)

    def fuse(
        self,
        work: Dict[str, Any],
        peer_eval: Dict[str, Any],
        stat_eval: Dict[str, Any],
        mismatch_eval: Dict[str, Any],
        dup_eval: Dict[str, Any]
    ) -> WorkRisk:
        # 1. Determine actual module availability BEFORE fusion
        def _get_active_score(eval_res: Dict[str, Any]) -> Optional[float]:
            if not eval_res.get("available", True):
                return None
            s = eval_res.get("score")
            if s is None:
                return None
            return float(s)

        module_scores = {
            "peer_benchmarking": _get_active_score(peer_eval),
            "statistical_outliers": _get_active_score(stat_eval),
            "financial_execution_mismatch": _get_active_score(mismatch_eval),
            "duplicate_overlap": _get_active_score(dup_eval),
        }

        # 2. Coverage analysis
        coverage = calculate_evidence_coverage(module_scores, work, mismatch_eval)

        # 2. Availability-normalized weighted average
        available_weights = coverage["available_weights"]
        sum_weight = coverage["sum_available_weight"]

        if sum_weight > 0.0:
            weighted_sum = sum(
                self.weights[mod] * module_scores[mod]
                for mod in available_weights
                if module_scores[mod] is not None
            )
            raw_score = weighted_sum / sum_weight
            final_score = round(min(100.0, max(0.0, raw_score)), 2)
            risk_band = determine_risk_band(final_score)
        else:
            final_score = None
            risk_band = "UNAVAILABLE"

        # 3. Compile structured evidence items
        evidence_objects: List[EvidenceItem] = []
        evidence_objects.extend(build_peer_evidence(peer_eval, work))
        evidence_objects.extend(build_stat_evidence(stat_eval, work))
        evidence_objects.extend(build_mismatch_evidence(mismatch_eval, work))
        evidence_objects.extend(build_duplicate_evidence(dup_eval, work))

        evidence_items_dicts = [item.to_dict() for item in evidence_objects]

        # 4. Collect all reason codes
        all_reason_codes = []
        for res in (peer_eval, stat_eval, mismatch_eval, dup_eval):
            all_reason_codes.extend(res.get("reason_codes", []))

        # 5. Generate objective investigation actions
        actions = generate_investigation_actions(
            risk_score=final_score if final_score is not None else 0.0,
            risk_band=risk_band,
            module_scores=module_scores,
            all_reason_codes=all_reason_codes,
            evidence_items=evidence_items_dicts,
            work=work
        )

        # 6. Work identification
        work_id = (
            work.get("unique_work_number")
            or f"DTL_{work.get('work_recommendation_dtl_id')}"
            or "UNKNOWN_WORK"
        )

        metadata = {
            "work_recommendation_dtl_id": work.get("work_recommendation_dtl_id"),
            "unique_work_number": work.get("unique_work_number"),
            "mp_name": work.get("mp_name"),
            "state": work.get("state"),
            "constituency": work.get("constituency"),
            "district": work.get("district"),
            "category": work.get("category"),
            "work_description": work.get("work_description"),
            "work_stage": work.get("work_stage"),
            "amount_recommended": work.get("amount_recommended"),
            "amount_sanctioned": work.get("amount_sanctioned"),
            "amount_completed": work.get("amount_completed"),
            "total_disbursed_amount": work.get("total_disbursed_amount"),
            "is_completed": work.get("is_completed", False),
            "source_provenance": "18th_lok_sabha_mospi_api"
        }

        return WorkRisk(
            work_id=work_id,
            risk_score=final_score,
            risk_band=risk_band,
            evidence_coverage=coverage,
            module_scores=module_scores,
            evidence_items=evidence_items_dicts,
            investigation_actions=actions,
            work_metadata=metadata
        )
