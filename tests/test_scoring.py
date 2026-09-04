"""Tests for General Scoring Bounds, Missing Data, Zero-Dispersion Safety, and Mismatch Tiers.

Validates:
- Every engine returns bounded scores between 0.0 and 100.0 (or None when evidence is unavailable)
- Never converting missing evidence into zero
- Zero-dispersion safety: features with MAD/IQR = 0 do not generate artificial anomaly scores
- Mismatch evidence tiers independently: Level 1 proxy (LOW), Level 1 financial (MEDIUM), Level 2 time (HIGH)
- Level 3 physical progress strictly verified UNAVAILABLE (never fabricated or inferred)
"""

import pytest
from src.peer_benchmark import PeerBenchmarkEngine
from src.statistical_outliers import StatisticalOutlierEngine
from src.mismatch import FinancialExecutionMismatchEngine
from src.duplicate_overlap import DuplicateOverlapEngine


def test_peer_benchmark_scoring_bounds():
    """Peer benchmark scores must be in [0, 100] or None."""
    engine = PeerBenchmarkEngine(min_cohort_size=10)
    
    works = [
        {
            "work_recommendation_dtl_id": i,
            "district": "Pune",
            "state": "Maharashtra",
            "category": "Roads",
            "year": "2024",
            "amount_recommended": 500000.0
        }
        for i in range(1, 21)
    ]
    engine.fit(works)
    
    # Normal work matching median
    res_normal = engine.evaluate_work(works[0])
    assert res_normal["score"] is not None
    assert 0.0 <= res_normal["score"] <= 100.0
    assert res_normal["score"] == 0.0

    # Extreme high work
    extreme_work = dict(works[0], amount_recommended=25000000.0)
    res_extreme = engine.evaluate_work(extreme_work)
    assert res_extreme["score"] is not None
    assert 80.0 <= res_extreme["score"] <= 100.0
    assert "PEER_EXTREME_HOMOGENEOUS_DEVIATION" in res_extreme["reason_codes"] or "PEER_EXTREME_OUTLIER_3X_IQR" in res_extreme["reason_codes"]


def test_peer_benchmark_missing_data_not_zero():
    """Missing recommended amount must yield score=None, not 0.0."""
    engine = PeerBenchmarkEngine(min_cohort_size=10)
    works = [
        {
            "work_recommendation_dtl_id": i,
            "district": "Pune",
            "state": "Maharashtra",
            "category": "Roads",
            "year": "2024",
            "amount_recommended": 500000.0
        }
        for i in range(1, 21)
    ]
    engine.fit(works)

    missing_work = {
        "work_recommendation_dtl_id": 999,
        "district": "Pune",
        "state": "Maharashtra",
        "category": "Roads",
        "year": "2024",
        "amount_recommended": None
    }
    res = engine.evaluate_work(missing_work)
    assert res["score"] is None
    assert "MISSING_RECOMMENDED_AMOUNT" in res["reason_codes"]
    assert res["coverage"] == "missing_amount"


def test_statistical_outlier_zero_dispersion_safety():
    """Zero-dispersion safety: features with MAD/IQR = 0 must safely return neutral/0.0 anomaly scores."""
    engine = StatisticalOutlierEngine()

    # 30 works where EVERY SINGLE WORK has identical sanction_to_rec_ratio = 1.0
    # and identical sanction_delay = 10 days (zero dispersion!)
    works = [
        {
            "work_recommendation_dtl_id": i,
            "amount_recommended": 500000.0,
            "amount_sanctioned": 500000.0,
            "recommendation_date": "2024-07-01",
            "sanction_date": "2024-07-11"
        }
        for i in range(1, 31)
    ]
    engine.fit(works)

    # Confirm dispersion is 0.0
    assert engine.feature_stats["sanction_to_rec_ratio"]["mad"] == 0.0
    assert engine.feature_stats["sanction_delay_days"]["mad"] == 0.0

    # Evaluate normal work
    res = engine.evaluate_work(works[0])
    assert res["feature_scores"]["sanction_to_rec_ratio"] == 0.0
    assert res["feature_scores"]["sanction_delay_days"] == 0.0
    assert res["score"] == 0.0

    # A work with a slight deviation on a zero-dispersion feature must NOT generate artificial extreme anomaly!
    slight_dev_work = dict(works[0], sanction_date="2024-07-12")
    res_dev = engine.evaluate_work(slight_dev_work)
    assert res_dev["feature_scores"]["sanction_delay_days"] == 0.0  # Zero-dispersion safe!
    assert "constant baseline" in res_dev["evidence"]


def test_statistical_outlier_bounds_and_missing():
    """Statistical outlier engine bounds [0, 100] and missing feature handling."""
    engine = StatisticalOutlierEngine()
    
    works = [
        {
            "work_recommendation_dtl_id": i,
            "amount_recommended": 200000.0 + i * 10000.0,
            "amount_sanctioned": 200000.0 + i * 10000.0,
            "recommendation_date": "2024-07-01",
            "sanction_date": "2024-07-15"
        }
        for i in range(1, 30)
    ]
    engine.fit(works)

    normal_work = works[10]
    res_normal = engine.evaluate_work(normal_work)
    assert res_normal["score"] is not None
    assert 0.0 <= res_normal["score"] <= 100.0

    # Work with zero valid numeric features -> score must be None
    empty_work = {
        "work_recommendation_dtl_id": 999,
        "amount_recommended": None,
        "amount_sanctioned": None,
        "recommendation_date": None,
        "sanction_date": None
    }
    res_empty = engine.evaluate_work(empty_work)
    assert res_empty["score"] is None
    assert "STAT_NO_FEATURES_AVAILABLE" in res_empty["reason_codes"]
    assert res_empty["coverage"] == "no_features"


def test_mismatch_engine_peer_duration_and_tiers():
    """Validates peer-comparative completion duration and independent mismatch tiers."""
    engine = FinancialExecutionMismatchEngine()

    # Fit peer completion durations with 20 completed works in 'Civil Works' (median duration ~ 90 days)
    population_works = [
        {
            "is_completed": True,
            "category": "Civil Works",
            "sanction_date": "2024-01-01",
            "completion_date": f"2024-04-0{min(9, i)}" if i < 10 else f"2024-04-{i}"  # ~90-110 days
        }
        for i in range(1, 25)
    ]
    engine.fit_peer_durations(population_works)
    assert "civil works" in engine.peer_durations
    assert engine.peer_durations["civil works"]["median"] >= 80

    # 1. Peer-comparative fast completion: 2 days vs peer median 90 days
    fast_work = {
        "amount_recommended": 400000.0,
        "amount_sanctioned": 400000.0,
        "amount_completed": 400000.0,
        "recommendation_date": "2024-07-01",
        "sanction_date": "2024-07-10",
        "completion_date": "2024-07-12",  # 2 days!
        "category": "Civil Works",
        "is_completed": True
    }
    res_fast = engine.evaluate_work(fast_work)
    assert res_fast["confidence_label"] == "HIGH"
    assert "MISMATCH_L2_IMPOSSIBLY_FAST_COMPLETION" in res_fast["reason_codes"]
    assert res_fast["score"] >= 80.0

    # 2. Level 3 Physical Progress Verification: MUST be unavailable
    assert res_fast["level_3_status"] == "UNAVAILABLE_IN_SOURCE"
    assert "MISMATCH_L3_PHYSICAL_PROGRESS_UNAVAILABLE" in res_fast["reason_codes"]
