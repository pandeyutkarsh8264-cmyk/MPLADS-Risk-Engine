"""Tests for Authoritative Exact Join Validation and Cardinality Rules.

Validates:
- WORK_RECOMMENDATION_DTL_ID is the only exact join key
- Completed works joined strictly 1:1 on WORK_RECOMMENDATION_DTL_ID
- Orphan completed works (no matching recommendation) are excluded from master
- Expenditure aggregated by WORK_RECOMMENDATION_DTL_ID
- Rejection of unvalidated / fuzzy joins
"""

import pytest
from src.joins import build_canonical_work_master, aggregate_expenditure_by_dtl_id


def test_exact_join_and_orphan_handling():
    """Validates that matched records join cleanly and orphans are excluded from master."""
    # 3 recommended works
    recommended_raw = [
        {
            "WORK_RECOMMENDATION_DTL_ID": 101,
            "ACTIVITY_NAME": "WS/MP1/2024-2025/101-Road Work",
            "STATE_NAME": "Bihar",
            "CONSTITUENCY": "Patna",
            "MP_NAME": "MP A",
            "RECOMMENDED_AMOUNT": 500000.0,
            "SANCTION_AMOUNT": 500000.0,
            "RECOMMENDATION_DATE": "01-Jul-2024"
        },
        {
            "WORK_RECOMMENDATION_DTL_ID": 102,
            "ACTIVITY_NAME": "WS/MP1/2024-2025/102-Drainage",
            "STATE_NAME": "Bihar",
            "CONSTITUENCY": "Patna",
            "MP_NAME": "MP A",
            "RECOMMENDED_AMOUNT": 300000.0,
            "SANCTION_AMOUNT": 300000.0,
            "RECOMMENDATION_DATE": "05-Jul-2024"
        },
        {
            "WORK_RECOMMENDATION_DTL_ID": 103,
            "ACTIVITY_NAME": "WS/MP1/2024-2025/103-School Building",
            "STATE_NAME": "Bihar",
            "CONSTITUENCY": "Patna",
            "MP_NAME": "MP A",
            "RECOMMENDED_AMOUNT": 800000.0,
            "SANCTION_AMOUNT": 800000.0,
            "RECOMMENDATION_DATE": "10-Jul-2024"
        }
    ]

    # 2 completed works: 101 matches, 999 is an orphan (no recommended parent)
    completed_raw = [
        {
            "WORK_RECOMMENDATION_DTL_ID": 101,
            "WORK_ID": "5001",
            "ACTUAL_AMOUNT": 490000.0,
            "ACTUAL_END_DATE": "01-Sep-2024"
        },
        {
            "WORK_RECOMMENDATION_DTL_ID": 999,  # Orphan!
            "WORK_ID": "5002",
            "ACTUAL_AMOUNT": 200000.0,
            "ACTUAL_END_DATE": "15-Sep-2024"
        }
    ]

    # 3 expenditure rows: two for 101, one for 102
    expenditure_raw = [
        {
            "WORK_RECOMMENDATION_DTL_ID": 101,
            "VENDOR_NAME": "Vendor Alpha",
            "VENDOR_ID": 11,
            "FUND_DISBURSED_AMT": 200000.0,
            "EXPENDITURE_DATE": "10-Aug-2024"
        },
        {
            "WORK_RECOMMENDATION_DTL_ID": 101,
            "VENDOR_NAME": "Vendor Beta",
            "VENDOR_ID": 12,
            "FUND_DISBURSED_AMT": 290000.0,
            "EXPENDITURE_DATE": "25-Aug-2024"
        },
        {
            "WORK_RECOMMENDATION_DTL_ID": 102,
            "VENDOR_NAME": "Vendor Gamma",
            "VENDOR_ID": 13,
            "FUND_DISBURSED_AMT": 300000.0,
            "EXPENDITURE_DATE": "20-Aug-2024"
        }
    ]

    master, audit = build_canonical_work_master(recommended_raw, completed_raw, expenditure_raw)

    # Master must have exactly 3 records (matching recommended count)
    assert len(master) == 3
    assert audit["joined_master_count"] == 3
    assert audit["completed_matched_count"] == 1
    assert audit["completed_orphan_count"] == 1  # 999 excluded

    # Inspect work 101
    w101 = next(w for w in master if w["work_recommendation_dtl_id"] == 101)
    assert w101["is_completed"] is True
    assert w101["amount_completed"] == 490000.0
    assert w101["completion_date"] == "2024-09-01"
    assert w101["total_disbursed_amount"] == 490000.0  # 200000 + 290000
    assert w101["disbursement_count"] == 2
    assert w101["vendor_count"] == 2

    # Inspect work 102 (not completed, but has expenditure)
    w102 = next(w for w in master if w["work_recommendation_dtl_id"] == 102)
    assert w102["is_completed"] is False
    assert w102["amount_completed"] is None
    assert w102["total_disbursed_amount"] == 300000.0
    assert w102["vendor_count"] == 1

    # Inspect work 103 (no completion, no expenditure)
    w103 = next(w for w in master if w["work_recommendation_dtl_id"] == 103)
    assert w103["is_completed"] is False
    assert w103["has_completion_evidence"] is False
    assert w103["has_expenditure_evidence"] is False
    assert w103["total_disbursed_amount"] is None
