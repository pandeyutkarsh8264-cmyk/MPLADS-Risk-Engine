"""Unit tests for the Next Intelligence Layer Upgrade.

Covers:
- Compliance Hub deterministic rule evaluation
- Agency / Implementing Entity concentration calculation
- Deterministic "What Should Be Checked Next?" directives
- Inspection Dossier HTML export completeness
"""

import pytest
import pandas as pd
from src.rules import evaluate_work_compliance
from src.investigation import generate_deterministic_next_checks
from src.ui_helpers import generate_inspection_dossier_html, render_compliance_audit_html, render_what_should_be_checked_next_html
from src.fusion import WorkRisk


def test_compliance_evaluation_complete_work():
    """Validates compliance evaluation on a fully conforming completed project."""
    record = {
        "work_recommendation_dtl_id": 133166,
        "state": "Karnataka",
        "constituency": "DHARWAD",
        "district": "DHARWAD",
        "mp_name": "Pralhad Venkatesh Joshi",
        "category": "Normal/Others",
        "implementing_authority": "DEPUTY COMMISSIONER DHARWAR",
        "amount_recommended": 500000.0,
        "amount_sanctioned": 500000.0,
        "total_disbursed_amount": 500000.0,
        "recommendation_date": "2024-07-08",
        "sanction_date": "2024-07-09",
        "completion_date": "2024-10-14",
        "is_completed": True,
        "amount_completed": 500000.0
    }
    result = evaluate_work_compliance(record)
    assert result["overall_status"] == "PASS"
    assert result["passed_count"] >= 4
    assert result["non_conforming_count"] == 0


def test_compliance_evaluation_missing_core_linkage():
    """Missing state or constituency triggers NON-CONFORMING status."""
    record = {
        "work_recommendation_dtl_id": 999999,
        "state": None,
        "constituency": "",
        "mp_name": None,
        "category": "Education",
        "amount_recommended": 100000.0
    }
    result = evaluate_work_compliance(record)
    assert result["overall_status"] == "NON-CONFORMING"
    admin_item = next(i for i in result["items"] if i["check_id"] == "ADMIN_LINKAGE")
    assert admin_item["status"] == "NON-CONFORMING"


def test_compliance_evaluation_unavailable_records():
    """In-progress projects with missing disbursement return UNAVAILABLE without error."""
    record = {
        "work_recommendation_dtl_id": 303957,
        "state": "Bihar",
        "constituency": "SARAN",
        "district": "SARAN",
        "mp_name": "Rajiv Pratap Rudy",
        "category": "Sports",
        "implementing_authority": "DISTRICT PLANNING OFFICE SARAN",
        "amount_recommended": 99965000.0,
        "amount_sanctioned": 99965000.0,
        "total_disbursed_amount": None,
        "is_completed": False
    }
    result = evaluate_work_compliance(record)
    fin_item = next(i for i in result["items"] if i["check_id"] == "FINANCIAL_SEQUENCE")
    assert fin_item["status"] == "UNAVAILABLE"
    assert "UNAVAILABLE" in fin_item["detail"]


def test_deterministic_next_checks_evidence_driven():
    """Directives adapt deterministically based on observed engine scores and coverage."""
    risk_obj = WorkRisk(
        work_id="TEST_01",
        risk_score=84.85,
        risk_band="CRITICAL",
        evidence_coverage={"available_weight_pct": 55.0},
        module_scores={"peer_benchmarking": 100.0, "statistical_outliers": 66.67, "financial_execution_mismatch": None, "duplicate_overlap": None},
        evidence_items=[],
        investigation_actions=["Action 1", "Action 2"],
        work_metadata={"amount_recommended": 99965000.0}
    )
    p_res = {"score": 100.0}
    s_res = {"score": 66.67}
    m_res = {"score": None, "available": False}
    d_res = {"score": None, "available": False}

    directives = generate_deterministic_next_checks(risk_obj, {}, p_res, s_res, m_res, d_res)
    assert len(directives) >= 2
    categories = [d["category"] for d in directives]
    assert "Evidence Completeness" in categories
    assert "Peer & Cost Benchmarking" in categories

    # Verify neutral tone — no defamatory accusations
    forbidden_terms = ["fraud", "corruption", "guilt", "guilty", "crime", "criminal", "fraudulent"]
    for d in directives:
        combined_text = (d["action"] + " " + d["rationale"]).lower()
        for term in forbidden_terms:
            assert term not in combined_text, f"Forbidden term '{term}' found in directive: {d}"


def test_inspection_dossier_html_completeness():
    """Generates inspection dossier and checks presence of compliance, agency, and next checks."""
    risk_obj = WorkRisk(
        work_id="DTL_303957",
        risk_score=84.85,
        risk_band="CRITICAL",
        evidence_coverage={"available_weight_pct": 55.0},
        module_scores={"peer_benchmarking": 100.0, "statistical_outliers": 66.67, "financial_execution_mismatch": None, "duplicate_overlap": None},
        evidence_items=[],
        investigation_actions=["Review DPR", "Inspect site markers"],
        work_metadata={"amount_recommended": 99965000.0}
    )
    record = {
        "work_recommendation_dtl_id": 303957,
        "work_id": "WS/MP/303957",
        "state": "Bihar",
        "constituency": "SARAN",
        "district": "SARAN",
        "mp_name": "Rajiv Pratap Rudy",
        "category": "Sports",
        "work_stage": "Recommended",
        "work_description": "Construction of Modern Indoor Stadium",
        "implementing_authority": "DISTRICT PLANNING OFFICE SARAN CHAPRA",
        "amount_recommended": 99965000.0,
        "amount_sanctioned": 99965000.0
    }
    html = generate_inspection_dossier_html(
        work_risk=risk_obj,
        work_record=record,
        p_res={"score": 100.0, "peer_median": 500000.0, "cohort_label": "district_category_year"},
        s_res={"score": 66.67, "evidence": "Statistical deviation."},
        m_res=None,
        d_res=None,
        review_status="Escalated for Field Inspection",
        review_notes="Priority inspection scheduled."
    )

    assert "MPPrisma — Project Inspection Dossier" in html
    assert "DISTRICT PLANNING OFFICE SARAN CHAPRA" in html
    assert "Compliance Hub Audit Matrix" in html
    assert "What Should Be Checked Next?" in html
    assert "@media print" in html
    assert "Review status and notes are session-scoped" in html
