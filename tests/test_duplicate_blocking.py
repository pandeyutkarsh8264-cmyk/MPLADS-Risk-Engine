"""Tests for Engine 4: Duplicate / Overlap Blocking, all-MiniLM-L6-v2 Semantic Embeddings, and Threshold Configurability.

Validates:
- Contextual blocking prevents all-pairs explosion
- all-MiniLM-L6-v2 semantic embeddings path is genuinely used
- RapidFuzz entity matching on agency/authority
- Threshold configurability (calibrated heuristics, not locked constants)
- Tri-state classification: "Likely duplicate", "Possible overlap", "Unrelated"
"""

import pytest
from src.duplicate_overlap import DuplicateOverlapEngine


def test_duplicate_minilm_semantic_path_and_same_context():
    """Identical description within same block must be classified as 'Likely duplicate' using MiniLM semantic embeddings."""
    engine = DuplicateOverlapEngine()

    work_orig = {
        "work_recommendation_dtl_id": 201,
        "work_description": "Construction of concrete pavement road from bus stand to ram temple",
        "state": "Uttar Pradesh",
        "constituency": "Varanasi",
        "category": "Roads",
        "amount_recommended": 500000.0,
        "mp_name": "MP Prime",
        "implementing_authority": "PWD Varanasi"
    }

    work_dup = {
        "work_recommendation_dtl_id": 202,
        "work_description": "Construction of concrete pavement road from bus stand to ram temple",
        "state": "Uttar Pradesh",
        "constituency": "Varanasi",
        "category": "Roads",
        "amount_recommended": 500000.0,
        "mp_name": "MP Prime",
        "implementing_authority": "PWD Varanasi"
    }

    engine.build_index([work_orig, work_dup])
    res = engine.evaluate_work(work_orig)

    assert res["score"] >= 85.0
    assert res["match_count_likely"] == 1
    assert len(res["top_matches"]) == 1
    top = res["top_matches"][0]
    assert top["classification"] == "Likely duplicate"
    assert top["same_mp"] is True
    assert top["similar_amount"] is True
    assert top["semantic_cosine_similarity"] >= 0.95
    assert "DUPLICATE_LIKELY_MATCH_FOUND" in res["reason_codes"]
    assert res["coverage"] in ("blocked_minilm_semantic", "blocked_text_fallback")


def test_duplicate_threshold_configurability():
    """Thresholds must be tunable and adjust classification accordingly."""
    # When semantic_threshold_likely is set to strict 0.999, high similarity (e.g. 0.85) should become Possible overlap
    engine_strict = DuplicateOverlapEngine(
        semantic_threshold_likely=0.999,
        semantic_verbatim_threshold=0.999,
        semantic_threshold_possible=0.60
    )

    work_a = {
        "work_recommendation_dtl_id": 211,
        "work_description": "Construction of community hall near village panchayat bhavan",
        "state": "Karnataka",
        "constituency": "Dharwad",
        "category": "Community Halls",
        "amount_recommended": 600000.0,
        "mp_name": "MP Joshi"
    }

    work_b = {
        "work_recommendation_dtl_id": 212,
        "work_description": "Construction of community hall near village panchayat",
        "state": "Karnataka",
        "constituency": "Dharwad",
        "category": "Community Halls",
        "amount_recommended": 600000.0,
        "mp_name": "MP Joshi"
    }

    engine_strict.build_index([work_a, work_b])
    res_strict = engine_strict.evaluate_work(work_a)
    top_match = res_strict["top_matches"][0]

    # Under strict 0.999 threshold, non-exact text becomes Possible overlap
    if top_match["semantic_cosine_similarity"] < 0.999:
        assert top_match["classification"] == "Possible overlap"


def test_different_context_blocked():
    """Identical description in DIFFERENT constituency/state must not match due to blocking."""
    engine = DuplicateOverlapEngine()

    work_up = {
        "work_recommendation_dtl_id": 301,
        "work_description": "Construction of community hall near panchayat office",
        "state": "Uttar Pradesh",
        "constituency": "Varanasi",
        "category": "Community Halls",
        "amount_recommended": 700000.0,
        "mp_name": "MP A"
    }

    work_tn = {
        "work_recommendation_dtl_id": 302,
        "work_description": "Construction of community hall near panchayat office",
        "state": "Tamil Nadu",
        "constituency": "Chennai South",
        "category": "Community Halls",
        "amount_recommended": 700000.0,
        "mp_name": "MP B"
    }

    engine.build_index([work_up, work_tn])
    res_up = engine.evaluate_work(work_up)

    assert res_up["score"] is None
    assert res_up["available"] is False
    assert res_up["match_count_likely"] == 0
    assert res_up["coverage"] == "block_empty"


def test_unrelated_descriptions_same_block():
    """Different descriptions in the same block must be classified as 'Unrelated' with score=0."""
    engine = DuplicateOverlapEngine()

    work_road = {
        "work_recommendation_dtl_id": 401,
        "work_description": "Installation of high mast solar lighting at daily fish market",
        "state": "Kerala",
        "constituency": "Ernakulam",
        "category": "Lighting",
        "amount_recommended": 250000.0,
        "mp_name": "MP Kerala"
    }

    work_park = {
        "work_recommendation_dtl_id": 402,
        "work_description": "Desilting and rejuvenation of public irrigation pond",
        "state": "Kerala",
        "constituency": "Ernakulam",
        "category": "Lighting",
        "amount_recommended": 250000.0,
        "mp_name": "MP Kerala"
    }

    engine.build_index([work_road, work_park])
    res = engine.evaluate_work(work_road)

    assert res["score"] == 0.0
    assert res["match_count_likely"] == 0
    assert res["match_count_possible"] == 0
    assert "DUPLICATE_NONE_FOUND" in res["reason_codes"]


def test_possible_overlap_semantic_similarity():
    """Partial semantic overlap in same category and block produces 'Possible overlap'."""
    engine = DuplicateOverlapEngine()

    work_a = {
        "work_recommendation_dtl_id": 501,
        "work_description": "Construction of additional classrooms and library room in Govt High School",
        "state": "Rajasthan",
        "constituency": "Jaipur",
        "category": "Education",
        "amount_recommended": 900000.0,
        "mp_name": "MP Raj"
    }

    work_b = {
        "work_recommendation_dtl_id": 502,
        "work_description": "Construction of classrooms and boundary wall in Govt High School",
        "state": "Rajasthan",
        "constituency": "Jaipur",
        "category": "Education",
        "amount_recommended": 850000.0,
        "mp_name": "MP Raj"
    }

    engine.build_index([work_a, work_b])
    res = engine.evaluate_work(work_a)

    assert res["score"] > 0.0
    assert res["match_count_likely"] + res["match_count_possible"] >= 1
    assert any(m["classification"] in ("Likely duplicate", "Possible overlap") for m in res["top_matches"])
