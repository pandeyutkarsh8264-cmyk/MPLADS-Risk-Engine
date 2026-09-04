"""Tests for Step 5: Availability-Normalized Evidence Fusion, Coverage, and WorkRisk.

Validates:
- All 4 modules available
- One module missing (renormalization)
- Multiple modules missing (renormalization)
- All modules missing (score=None, band="UNAVAILABLE")
- Correct weight renormalization formula
- Score bounds [0.0, 100.0]
- Risk bands: 0–29 LOW, 30–59 MEDIUM, 60–79 HIGH, 80–100 CRITICAL
- Structured evidence item traceability
- Proxy vs observed confidence tracking
- No-fabrication behavior: Level 3 physical progress strictly unavailable
- Objective investigation actions without fraud/guilt claims
"""

import pytest
from src.fusion import RiskFusionEngine, determine_risk_band, WorkRisk
from src.coverage import calculate_evidence_coverage, LOCKED_WEIGHTS


@pytest.fixture
def mock_work():
    return {
        "work_recommendation_dtl_id": 1001,
        "unique_work_number": "WS/MP100/2024-2025/1001",
        "mp_name": "Sample MP",
        "state": "Maharashtra",
        "constituency": "Pune",
        "district": "Pune",
        "category": "Roads",
        "work_description": "Construction of road from village square to hospital",
        "work_stage": "Completed",
        "amount_recommended": 500000.0,
        "amount_sanctioned": 500000.0,
        "amount_completed": 500000.0,
        "total_disbursed_amount": 500000.0,
        "is_completed": True,
        "has_completion_evidence": True,
        "has_expenditure_evidence": True
    }


def test_fusion_all_four_modules_available(mock_work):
    """When all 4 modules are available, weights must equal 0.30, 0.25, 0.30, 0.15."""
    engine = RiskFusionEngine()

    peer_eval = {"score": 40.0, "reason_codes": [], "cohort_level": 1, "cohort_size": 20, "peer_median": 450000.0}
    stat_eval = {"score": 20.0, "reason_codes": [], "feature_scores": {"amount_recommended": 20.0}}
    mismatch_eval = {"score": 30.0, "reason_codes": [], "confidence_label": "HIGH", "signals": []}
    dup_eval = {"score": 10.0, "reason_codes": [], "top_matches": []}

    work_risk = engine.fuse(mock_work, peer_eval, stat_eval, mismatch_eval, dup_eval)

    # Expected score: 0.30*40 + 0.25*20 + 0.30*30 + 0.15*10 = 12 + 5 + 9 + 1.5 = 27.5
    assert work_risk.risk_score == 27.5
    assert work_risk.risk_band == "LOW"
    assert work_risk.evidence_coverage["available_weight_pct"] == 100.0
    assert len(work_risk.evidence_coverage["modules_available"]) == 4
    assert len(work_risk.evidence_coverage["modules_missing"]) == 0
    assert work_risk.evidence_coverage["observed_vs_proxy"] == "fully_observed"


def test_fusion_one_module_missing_renormalization(mock_work):
    """When one module is missing, remaining weights must renormalize to 1.0."""
    engine = RiskFusionEngine()

    # Peer is missing (score=None)
    peer_eval = {"score": None, "reason_codes": ["PEER_INSUFFICIENT_COHORT"]}
    stat_eval = {"score": 60.0, "reason_codes": []}
    mismatch_eval = {"score": 80.0, "reason_codes": [], "confidence_label": "HIGH"}
    dup_eval = {"score": 40.0, "reason_codes": []}

    work_risk = engine.fuse(mock_work, peer_eval, stat_eval, mismatch_eval, dup_eval)

    # Available weights: stat (0.25) + mismatch (0.30) + dup (0.15) = 0.70
    # Expected score: (0.25*60 + 0.30*80 + 0.15*40) / 0.70 = (15 + 24 + 6) / 0.70 = 45 / 0.70 = 64.29
    assert work_risk.risk_score == 64.29
    assert work_risk.risk_band == "HIGH"
    assert work_risk.evidence_coverage["available_weight_pct"] == 70.0
    assert "peer_benchmarking" in work_risk.evidence_coverage["modules_missing"]
    assert work_risk.module_scores["peer_benchmarking"] is None


def test_fusion_multiple_modules_missing(mock_work):
    """When multiple modules are missing, remaining weights renormalize cleanly."""
    engine = RiskFusionEngine()

    # Peer and Duplicate missing -> only stat (0.25) and mismatch (0.30) available
    peer_eval = {"score": None, "reason_codes": []}
    stat_eval = {"score": 40.0, "reason_codes": []}
    mismatch_eval = {"score": 90.0, "reason_codes": [], "confidence_label": "MEDIUM"}
    dup_eval = {"score": None, "reason_codes": []}

    work_risk = engine.fuse(mock_work, peer_eval, stat_eval, mismatch_eval, dup_eval)

    # Available weights: 0.25 + 0.30 = 0.55
    # Expected score: (0.25*40 + 0.30*90) / 0.55 = (10 + 27) / 0.55 = 37 / 0.55 = 67.27
    assert work_risk.risk_score == 67.27
    assert work_risk.risk_band == "HIGH"
    assert work_risk.evidence_coverage["available_weight_pct"] == 55.0
    assert len(work_risk.evidence_coverage["modules_available"]) == 2


def test_fusion_all_modules_missing(mock_work):
    """When all modules are missing, score must be None and band 'UNAVAILABLE'."""
    engine = RiskFusionEngine()

    peer_eval = {"score": None}
    stat_eval = {"score": None}
    mismatch_eval = {"score": None}
    dup_eval = {"score": None}

    work_risk = engine.fuse(mock_work, peer_eval, stat_eval, mismatch_eval, dup_eval)

    assert work_risk.risk_score is None
    assert work_risk.risk_band == "UNAVAILABLE"
    assert work_risk.evidence_coverage["available_weight_pct"] == 0.0
    assert len(work_risk.evidence_coverage["modules_missing"]) == 4


def test_risk_bands_exact():
    """Validates exact risk bands: 0-29 LOW, 30-59 MEDIUM, 60-79 HIGH, 80-100 CRITICAL."""
    assert determine_risk_band(0.0) == "LOW"
    assert determine_risk_band(29.99) == "LOW"
    assert determine_risk_band(30.0) == "MEDIUM"
    assert determine_risk_band(59.99) == "MEDIUM"
    assert determine_risk_band(60.0) == "HIGH"
    assert determine_risk_band(79.99) == "HIGH"
    assert determine_risk_band(80.0) == "CRITICAL"
    assert determine_risk_band(100.0) == "CRITICAL"
    assert determine_risk_band(None) == "UNAVAILABLE"


def test_evidence_traceability_and_structure(mock_work):
    """Every evidence item must have all required fields and trace to a source dataset."""
    engine = RiskFusionEngine()

    peer_eval = {"score": 30.0, "reason_codes": [], "cohort_level": 1, "cohort_level_name": "dist", "cohort_size": 15, "peer_median": 400000.0, "evidence": "Peer test evidence"}
    stat_eval = {"score": 15.0, "feature_scores": {"amount_recommended": 15.0}, "feature_zscores": {"amount_recommended": 1.2}}
    mismatch_eval = {"score": 0.0, "confidence_label": "HIGH", "signals": [], "evidence": "Mismatch clean", "reason_codes": []}
    dup_eval = {"score": 0.0, "top_matches": [], "evidence": "Duplicate clean", "reason_codes": []}

    work_risk = engine.fuse(mock_work, peer_eval, stat_eval, mismatch_eval, dup_eval)

    assert len(work_risk.evidence_items) >= 4
    for item in work_risk.evidence_items:
        assert "module" in item
        assert "metric" in item
        assert "observed_value" in item
        assert "comparison_value" in item
        assert "comparison_group" in item
        assert "explanation" in item
        assert "source_dataset" in item
        assert "confidence" in item
        assert "data_quality_flags" in item
        assert isinstance(item["data_quality_flags"], list)


def test_no_fabrication_level_3_physical_progress(mock_work):
    """Level 3 physical progress must be strictly recorded as unavailable, never fabricated."""
    engine = RiskFusionEngine()

    peer_eval = {"score": 20.0}
    stat_eval = {"score": 20.0}
    mismatch_eval = {"score": 0.0, "confidence_label": "LOW", "signals": []}
    dup_eval = {"score": 0.0, "top_matches": []}

    work_risk = engine.fuse(mock_work, peer_eval, stat_eval, mismatch_eval, dup_eval)

    # Check coverage
    assert work_risk.evidence_coverage["level_3_physical_progress_available"] is False
    assert work_risk.evidence_coverage["physical_progress_status"] == "UNAVAILABLE_IN_SOURCE"

    # Check evidence items
    l3_item = next(it for it in work_risk.evidence_items if it["metric"] == "level_3_physical_progress")
    assert l3_item["available"] is False
    assert l3_item["observed_value"] == "UNAVAILABLE"
    assert "not exist in source" in l3_item["explanation"].lower()


def test_investigation_actions_objective_no_fraud_claims(mock_work):
    """Investigation actions must use objective language and never claim fraud or guilt."""
    engine = RiskFusionEngine()

    # Extreme risk scenario
    peer_eval = {"score": 95.0, "reason_codes": ["PEER_EXTREME_OUTLIER_3X_IQR"]}
    stat_eval = {"score": 85.0, "reason_codes": ["STAT_EXTREME_OUTLIER_HIGH_AMOUNT_RECOMMENDED"]}
    mismatch_eval = {"score": 90.0, "reason_codes": ["MISMATCH_L1_EXTREME_COST_OVERRUN"], "signals": ["Extreme overrun"]}
    dup_eval = {"score": 95.0, "reason_codes": ["DUPLICATE_LIKELY_MATCH_FOUND"], "top_matches": [{"matched_work_dtl_id": 999, "classification": "Likely duplicate"}]}

    work_risk = engine.fuse(mock_work, peer_eval, stat_eval, mismatch_eval, dup_eval)

    assert work_risk.risk_score >= 80.0
    assert work_risk.risk_band == "CRITICAL"
    assert len(work_risk.investigation_actions) >= 3

    for act in work_risk.investigation_actions:
        lower_act = act.lower()
        # Strictly forbidden words
        assert "fraud" not in lower_act
        assert "guilt" not in lower_act
        assert "crime" not in lower_act
        assert "corrupt" not in lower_act
        # Objective review language present
        assert any(word in lower_act for word in ("review", "verify", "inspect", "audit", "reconcile", "inquire", "inquiry", "check", "assess"))


def test_real_data_style_two_modules_available_renormalization():
    """Validates the exact real-data scenario (e.g. DTL_303957) where only Peer and Statistical are available.

    Must verify:
    1. Correct renormalized score: (0.30*100 + 0.25*66.67) / (0.30 + 0.25) = 84.85
    2. Correct coverage: 55.0%
    3. Unavailable modules do not contribute zero (score != 46.67)
    4. module_scores has None for unavailable modules
    5. evidence_items has available=False for unavailable modules
    """
    real_work = {
        "work_recommendation_dtl_id": 303957,
        "unique_work_number": None,
        "mp_name": "Rajiv Pratap Rudy",
        "state": "Bihar",
        "constituency": "SARAN",
        "district": "SARAN",
        "category": "Normal/Others",
        "work_description": "Construction of a Modern Indoor Stadium Badminton Court",
        "work_stage": "Pending for Sanction",
        "amount_recommended": 99965000.0,
        "amount_sanctioned": 99965000.0,
        "sanction_date": None,
        "amount_completed": None,
        "total_disbursed_amount": None,
        "is_completed": False,
        "has_completion_evidence": False,
        "has_expenditure_evidence": False
    }

    engine = RiskFusionEngine()

    peer_eval = {
        "score": 100.0,
        "available": True,
        "cohort_level": 5,
        "cohort_level_name": "national_category",
        "cohort_size": 11,
        "peer_median": 450000.0,
        "percentile_rank": 100.0,
        "deviation_ratio": 222.1,
        "evidence": "Recommended amount ₹99,965,000 evaluated at Level 5."
    }
    stat_eval = {
        "score": 66.67,
        "available": True,
        "feature_scores": {"amount_recommended": 100.0, "amount_sanctioned": 100.0, "sanction_to_rec_ratio": 0.0},
        "evidence": "Evaluated on 3/6 available features."
    }
    # Mismatch is unavailable because there is no execution or financial realization evidence
    mismatch_eval = {
        "score": None,
        "available": False,
        "confidence_label": "NONE",
        "signals": [],
        "reason_codes": ["MISMATCH_EXECUTION_DATA_UNAVAILABLE"],
        "evidence": "Financial-execution mismatch unavailable: work lacks sanction, completion, and expenditure evidence."
    }
    # Duplicate is unavailable because candidate pool is empty or unavailable
    dup_eval = {
        "score": None,
        "available": False,
        "top_matches": [],
        "reason_codes": ["DUPLICATE_NO_BLOCK_CANDIDATES"],
        "evidence": "Duplicate detection unavailable: no other candidate works in contextual block."
    }

    work_risk = engine.fuse(real_work, peer_eval, stat_eval, mismatch_eval, dup_eval)

    # 1. Correct renormalized score: (0.30*100 + 0.25*66.67) / 0.55 = 46.6675 / 0.55 = 84.85
    assert work_risk.risk_score == 84.85
    assert work_risk.risk_band == "CRITICAL"

    # 2. Unavailable modules must NOT contribute zero (which would have yielded 46.67)
    assert work_risk.risk_score != 46.67

    # 3. Correct coverage
    assert work_risk.evidence_coverage["available_weight_pct"] == 55.0
    assert work_risk.evidence_coverage["sum_available_weight"] == 0.55
    assert set(work_risk.evidence_coverage["modules_available"]) == {"peer_benchmarking", "statistical_outliers"}
    assert set(work_risk.evidence_coverage["modules_missing"]) == {"financial_execution_mismatch", "duplicate_overlap"}

    # 4. Consistent module_scores (None for unavailable)
    assert work_risk.module_scores["peer_benchmarking"] == 100.0
    assert work_risk.module_scores["statistical_outliers"] == 66.67
    assert work_risk.module_scores["financial_execution_mismatch"] is None
    assert work_risk.module_scores["duplicate_overlap"] is None

    # 5. Evidence items show available=False for unavailable modules
    mismatch_ev = next(it for it in work_risk.evidence_items if it["module"] == "financial_execution_mismatch" and it["metric"] == "execution_financial_evidence")
    assert mismatch_ev["available"] is False
    assert mismatch_ev["score"] is None

    dup_ev = next(it for it in work_risk.evidence_items if it["module"] == "duplicate_overlap")
    assert dup_ev["available"] is False
    assert dup_ev["score"] is None

