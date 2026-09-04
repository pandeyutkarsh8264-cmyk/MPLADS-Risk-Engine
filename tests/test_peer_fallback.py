"""Tests for Engine 1: Exact 5-Step Peer Fallback Hierarchy.

Locked hierarchy:
  Step 1: same district + same category + same year
  Step 2: same district + same category
  Step 3: same state + same category + same year
  Step 4: same state + same category
  Step 5: national + same category

Validates:
- Minimum preferred cohort target = 10
- Immediate selection of first level with >= 10 peers
- Fallback progression from step 1 down to step 5
- Failure when national has < 10 peers (returns None, coverage="insufficient_peers")
"""

import pytest
from src.peer_benchmark import PeerBenchmarkEngine


def test_step_1_selection_when_cohort_sufficient():
    """When Step 1 (district+cat+year) has >= 10 works, it must be selected."""
    engine = PeerBenchmarkEngine(min_cohort_size=10)
    
    works = [
        {
            "work_recommendation_dtl_id": i,
            "district": "Pune",
            "state": "Maharashtra",
            "category": "Education",
            "year": "2024",
            "amount_recommended": 300000.0 + i * 5000.0
        }
        for i in range(1, 15)
    ]
    engine.fit(works)

    target = works[0]
    res = engine.evaluate_work(target)
    assert res["cohort_level"] == 1
    assert res["cohort_level_name"] == "district_category_year"
    assert res["cohort_size"] == 14
    assert res["coverage"] == "full"
    assert "COHORT_STEP_1_DISTRICT_CATEGORY_YEAR" in res["reason_codes"]


def test_step_2_fallback_when_year_split_thin():
    """If Step 1 has < 10 (e.g. 5 in 2024 and 8 in 2025), Step 2 (district+cat) with 13 must be selected."""
    engine = PeerBenchmarkEngine(min_cohort_size=10)
    
    # 5 works in 2024
    works_2024 = [
        {
            "work_recommendation_dtl_id": i,
            "district": "Pune",
            "state": "Maharashtra",
            "category": "Health",
            "year": "2024",
            "amount_recommended": 400000.0
        }
        for i in range(1, 6)
    ]
    # 8 works in 2025
    works_2025 = [
        {
            "work_recommendation_dtl_id": 100 + i,
            "district": "Pune",
            "state": "Maharashtra",
            "category": "Health",
            "year": "2025",
            "amount_recommended": 450000.0
        }
        for i in range(1, 9)
    ]
    engine.fit(works_2024 + works_2025)

    target = works_2024[0]
    res = engine.evaluate_work(target)
    assert res["cohort_level"] == 2
    assert res["cohort_level_name"] == "district_category"
    assert res["cohort_size"] == 13
    assert res["coverage"] == "fallback_step_2"
    assert "COHORT_STEP_2_DISTRICT_CATEGORY" in res["reason_codes"]


def test_step_3_fallback_to_state_year():
    """If district has < 10 total, but state in same year has >= 10, select Step 3."""
    engine = PeerBenchmarkEngine(min_cohort_size=10)
    
    # District 'Solapur' has only 3 works
    solapur_works = [
        {
            "work_recommendation_dtl_id": i,
            "district": "Solapur",
            "state": "Maharashtra",
            "category": "Water",
            "year": "2024",
            "amount_recommended": 200000.0
        }
        for i in range(1, 4)
    ]
    # Other districts in Maharashtra have 12 works in 2024
    other_mh_works = [
        {
            "work_recommendation_dtl_id": 10 + i,
            "district": "Nagpur",
            "state": "Maharashtra",
            "category": "Water",
            "year": "2024",
            "amount_recommended": 220000.0
        }
        for i in range(1, 13)
    ]
    engine.fit(solapur_works + other_mh_works)

    target = solapur_works[0]
    res = engine.evaluate_work(target)
    assert res["cohort_level"] == 3
    assert res["cohort_level_name"] == "state_category_year"
    assert res["cohort_size"] == 15
    assert res["coverage"] == "fallback_step_3"
    assert "COHORT_STEP_3_STATE_CATEGORY_YEAR" in res["reason_codes"]


def test_step_4_fallback_to_state_category():
    """If state same-year has < 10, but state all-years has >= 10, select Step 4."""
    engine = PeerBenchmarkEngine(min_cohort_size=10)
    
    # 4 works in 2024, 8 works in 2025, scattered across districts in Goa
    goa_2024 = [
        {
            "work_recommendation_dtl_id": i,
            "district": f"Goa_D_{i}",
            "state": "Goa",
            "category": "Sports",
            "year": "2024",
            "amount_recommended": 350000.0
        }
        for i in range(1, 5)
    ]
    goa_2025 = [
        {
            "work_recommendation_dtl_id": 10 + i,
            "district": f"Goa_D_{i}",
            "state": "Goa",
            "category": "Sports",
            "year": "2025",
            "amount_recommended": 360000.0
        }
        for i in range(1, 9)
    ]
    engine.fit(goa_2024 + goa_2025)

    target = goa_2024[0]
    res = engine.evaluate_work(target)
    assert res["cohort_level"] == 4
    assert res["cohort_level_name"] == "state_category"
    assert res["cohort_size"] == 12
    assert res["coverage"] == "fallback_step_4"
    assert "COHORT_STEP_4_STATE_CATEGORY" in res["reason_codes"]


def test_step_5_fallback_to_national():
    """If state has < 10 total, but national has >= 10, select Step 5."""
    engine = PeerBenchmarkEngine(min_cohort_size=10)
    
    # Sikkim has only 2 works
    sikkim_works = [
        {
            "work_recommendation_dtl_id": i,
            "district": "East Sikkim",
            "state": "Sikkim",
            "category": "Solar",
            "year": "2024",
            "amount_recommended": 800000.0
        }
        for i in range(1, 3)
    ]
    # Rest of India has 15 works
    national_works = [
        {
            "work_recommendation_dtl_id": 10 + i,
            "district": f"Dist_{i}",
            "state": f"State_{i}",
            "category": "Solar",
            "year": "2024",
            "amount_recommended": 750000.0
        }
        for i in range(1, 16)
    ]
    engine.fit(sikkim_works + national_works)

    target = sikkim_works[0]
    res = engine.evaluate_work(target)
    assert res["cohort_level"] == 5
    assert res["cohort_level_name"] == "national_category"
    assert res["cohort_size"] == 17
    assert res["coverage"] == "fallback_step_5"
    assert "COHORT_STEP_5_NATIONAL_CATEGORY" in res["reason_codes"]


def test_insufficient_peers_at_all_levels():
    """When even national has < 10 works, return score=None and coverage='insufficient_peers'."""
    engine = PeerBenchmarkEngine(min_cohort_size=10)
    
    # Only 4 works nationally in an obscure category
    rare_works = [
        {
            "work_recommendation_dtl_id": i,
            "district": f"Dist_{i}",
            "state": f"State_{i}",
            "category": "RareExperimentalCategory",
            "year": "2024",
            "amount_recommended": 1200000.0
        }
        for i in range(1, 5)
    ]
    engine.fit(rare_works)

    target = rare_works[0]
    res = engine.evaluate_work(target)
    assert res["score"] is None
    assert res["cohort_level"] is None
    assert res["cohort_size"] == 4
    assert res["coverage"] == "insufficient_peers"
    assert "PEER_INSUFFICIENT_COHORT" in res["reason_codes"]
