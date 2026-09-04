"""Structured Evidence Object Builder.

Every evidence item conforms to the locked specification requirements:
- module: str
- score: Optional[float]
- available: bool
- confidence: str ("LOW", "MEDIUM", "HIGH", "VERY HIGH", "NONE")
- metric: str
- observed_value: Any
- comparison_value: Any
- comparison_group: str
- explanation: str
- source_dataset: str
- data_quality_flags: List[str]
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict


@dataclass
class EvidenceItem:
    module: str
    metric: str
    observed_value: Any
    comparison_value: Any
    comparison_group: str
    explanation: str
    source_dataset: str
    available: bool = True
    score: Optional[float] = None
    confidence: str = "MEDIUM"
    data_quality_flags: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if d["data_quality_flags"] is None:
            d["data_quality_flags"] = []
        return d


def build_peer_evidence(peer_eval: Dict[str, Any], work: Dict[str, Any]) -> List[EvidenceItem]:
    """Extracts structured evidence items from Engine 1 Peer Benchmarking result."""
    items = []
    if peer_eval.get("score") is None:
        items.append(EvidenceItem(
            module="peer_benchmarking",
            metric="amount_recommended",
            observed_value=work.get("amount_recommended"),
            comparison_value=None,
            comparison_group="insufficient_peers",
            explanation=peer_eval.get("evidence", "No valid peer cohort met minimum size of 10."),
            source_dataset="works_recommended.json",
            available=False,
            score=None,
            confidence="NONE",
            data_quality_flags=["INSUFFICIENT_PEER_COHORT"]
        ))
        return items

    amt = work.get("amount_recommended")
    med = peer_eval.get("peer_median")
    cohort_name = peer_eval.get("cohort_level_name")
    n = peer_eval.get("cohort_size")
    pct = peer_eval.get("percentile_rank")
    dev = peer_eval.get("deviation_ratio")

    items.append(EvidenceItem(
        module="peer_benchmarking",
        metric="recommended_amount_vs_peer_median",
        observed_value=f"₹{amt:,.0f}" if amt else None,
        comparison_value=f"₹{med:,.0f}" if med else None,
        comparison_group=f"Step {peer_eval.get('cohort_level')}: {cohort_name} (n={n})",
        explanation=peer_eval.get("evidence", ""),
        source_dataset="works_recommended.json",
        available=True,
        score=peer_eval.get("score"),
        confidence="HIGH" if peer_eval.get("cohort_level") == 1 else "MEDIUM",
        data_quality_flags=[f"COHORT_SIZE_{n}"] + ([f"PERCENTILE_{pct:.0f}"] if pct else [])
    ))
    return items


def build_stat_evidence(stat_eval: Dict[str, Any], work: Dict[str, Any]) -> List[EvidenceItem]:
    """Extracts structured evidence items from Engine 2 Statistical Outliers result."""
    items = []
    if stat_eval.get("score") is None:
        items.append(EvidenceItem(
            module="statistical_outliers",
            metric="numeric_feature_anomalies",
            observed_value=None,
            comparison_value=None,
            comparison_group="population_baseline",
            explanation="No valid numeric features available for statistical anomaly evaluation.",
            source_dataset="works_recommended.json",
            available=False,
            score=None,
            confidence="NONE",
            data_quality_flags=["NO_NUMERIC_FEATURES"]
        ))
        return items

    feat_scores = stat_eval.get("feature_scores", {})
    feat_z = stat_eval.get("feature_zscores", {})

    for fname, sub_score in feat_scores.items():
        z_val = feat_z.get(fname, 0.0)
        flags = []
        if z_val >= 6.0:
            flags.append("EXTREME_MOD_Z")
        elif z_val >= 3.5:
            flags.append("MOD_Z_OUTLIER")

        # Determine source dataset based on feature
        if "completed" in fname:
            src = "works_completed.json"
        elif "disbursed" in fname:
            src = "expenditure_completed_ongoing.json"
        else:
            src = "works_recommended.json"

        items.append(EvidenceItem(
            module="statistical_outliers",
            metric=fname,
            observed_value=work.get(fname) or work.get(fname.replace("_ratio", "")),
            comparison_value=f"mod_z={z_val:.2f}",
            comparison_group="18th_lok_sabha_population_baseline",
            explanation=f"Feature {fname} sub-score: {sub_score:.1f} (Modified Z={z_val:.2f}).",
            source_dataset=src,
            available=True,
            score=sub_score,
            confidence="HIGH" if z_val > 0 else "MEDIUM",
            data_quality_flags=flags
        ))
    return items


def build_mismatch_evidence(mismatch_eval: Dict[str, Any], work: Dict[str, Any]) -> List[EvidenceItem]:
    """Extracts structured evidence items from Engine 3 Financial-Execution Mismatch result."""
    items = []
    is_avail = mismatch_eval.get("available", False) and (mismatch_eval.get("score") is not None)
    conf = mismatch_eval.get("confidence_label", "LOW")
    signals = mismatch_eval.get("signals", [])

    if not is_avail:
        items.append(EvidenceItem(
            module="financial_execution_mismatch",
            metric="execution_financial_evidence",
            observed_value=work.get("work_stage"),
            comparison_value="None",
            comparison_group="execution_milestones",
            explanation=mismatch_eval.get("evidence", "Financial-execution mismatch unavailable: work lacks sanction, completion, and expenditure evidence."),
            source_dataset="none",
            available=False,
            score=None,
            confidence="NONE",
            data_quality_flags=["MISMATCH_DATA_UNAVAILABLE"]
        ))
    elif not signals:
        items.append(EvidenceItem(
            module="financial_execution_mismatch",
            metric="milestone_financial_alignment",
            observed_value=work.get("work_stage"),
            comparison_value="Aligned",
            comparison_group="statutory_milestones",
            explanation=mismatch_eval.get("evidence", "No mismatch detected."),
            source_dataset="works_recommended.json + works_completed.json",
            available=True,
            score=0.0,
            confidence=conf,
            data_quality_flags=["NO_MISMATCH_DETECTED"]
        ))
    else:
        for sig in signals:
            items.append(EvidenceItem(
                module="financial_execution_mismatch",
                metric="execution_or_timeline_anomaly",
                observed_value=sig,
                comparison_value="Departmental norms / peer duration",
                comparison_group="peer_execution_distribution",
                explanation=sig,
                source_dataset="works_recommended.json + works_completed.json + expenditure_completed_ongoing.json",
                available=True,
                score=mismatch_eval.get("score"),
                confidence=conf,
                data_quality_flags=[f"TIER_{conf}"]
            ))

    # Always append Level 3 physical progress item (strictly unavailable in public source)
    items.append(EvidenceItem(
        module="financial_execution_mismatch",
        metric="level_3_physical_progress",
        observed_value="UNAVAILABLE",
        comparison_value="0% in public dataset",
        comparison_group="authoritative_physical_progress",
        explanation="Authoritative physical progress percentage does not exist in source data. Not inferred or fabricated.",
        source_dataset="none",
        available=False,
        score=None,
        confidence="VERY HIGH",
        data_quality_flags=["LEVEL_3_PHYSICAL_PROGRESS_UNAVAILABLE"]
    ))
    return items


def build_duplicate_evidence(dup_eval: Dict[str, Any], work: Dict[str, Any]) -> List[EvidenceItem]:
    """Extracts structured evidence items from Engine 4 Duplicate/Overlap result."""
    items = []
    is_avail = dup_eval.get("available", False) and (dup_eval.get("score") is not None)
    top_matches = dup_eval.get("top_matches", [])

    raw_desc = work.get("work_description")
    desc_sample = raw_desc[:100] if isinstance(raw_desc, str) else None

    if not is_avail:
        items.append(EvidenceItem(
            module="duplicate_overlap",
            metric="candidate_block_comparison",
            observed_value=desc_sample,
            comparison_value="None",
            comparison_group="contextual_candidate_block",
            explanation=dup_eval.get("evidence", "Duplicate detection unavailable: no candidates or insufficient text."),
            source_dataset="works_recommended.json",
            available=False,
            score=None,
            confidence="NONE",
            data_quality_flags=["DUPLICATE_DATA_UNAVAILABLE"]
        ))
    elif not top_matches:
        items.append(EvidenceItem(
            module="duplicate_overlap",
            metric="semantic_and_entity_similarity",
            observed_value=desc_sample,
            comparison_value="No candidate matches in contextual block",
            comparison_group="contextual_candidate_block",
            explanation=dup_eval.get("evidence", "No duplicates or overlaps detected."),
            source_dataset="works_recommended.json",
            available=True,
            score=0.0,
            confidence="HIGH",
            data_quality_flags=["NO_DUPLICATES_DETECTED"]
        ))
    else:
        for match in top_matches:
            items.append(EvidenceItem(
                module="duplicate_overlap",
                metric=f"semantic_similarity_with_DTL_{match['matched_work_dtl_id']}",
                observed_value=work.get("work_description")[:100] if work.get("work_description") else None,
                comparison_value=match.get("matched_work_description"),
                comparison_group=f"Context Block: {work.get('state')}, {work.get('constituency')}, {work.get('category')}",
                explanation=(
                    f"Match classified as '{match.get('classification')}' "
                    f"(semantic cosine: {match.get('semantic_cosine_similarity')}, "
                    f"agency sim: {match.get('agency_similarity')}%, same MP: {match.get('same_mp')}, "
                    f"similar amount: {match.get('similar_amount')})."
                ),
                source_dataset="works_recommended.json",
                available=True,
                score=match.get("match_weight"),
                confidence="HIGH" if match.get("classification") == "Likely duplicate" else "MEDIUM",
                data_quality_flags=[f"CLASS_{match.get('classification').replace(' ', '_').upper()}"]
            ))
    return items
