"""Authoritative Exact Join Module for MPLADS Engine.

Strictly adheres to approved Step 3 findings and decisions:
1. WORK_RECOMMENDATION_DTL_ID is the authoritative exact join key.
2. Completed works joined strictly 1:1 on WORK_RECOMMENDATION_DTL_ID.
3. 130 orphan completed works are excluded from joined master (retained in audit).
4. Expenditure is aggregated by WORK_RECOMMENDATION_DTL_ID (1:many relation)
   yielding work-level disbursement totals, vendor counts, and latest payment dates.
5. No fuzzy matching or unvalidated joins.
"""

from typing import Dict, Any, List, Tuple
from collections import defaultdict

from src.canonical import (
    canonicalize_recommended,
    canonicalize_completed,
    canonicalize_expenditure,
    canonicalize_allocation
)


def aggregate_expenditure_by_dtl_id(
    expenditure_records: List[Dict[str, Any]]
) -> Dict[Any, Dict[str, Any]]:
    """Aggregates raw or canonical expenditure records by WORK_RECOMMENDATION_DTL_ID."""
    agg = defaultdict(lambda: {
        "total_disbursed_amount": 0.0,
        "disbursement_count": 0,
        "vendors": set(),
        "vendor_ids": set(),
        "latest_expenditure_date": None,
        "payment_statuses": set(),
        "implementing_agencies": set(),
    })

    for exp_raw in expenditure_records:
        rec = canonicalize_expenditure(exp_raw)
        dtl_id = rec.get("work_recommendation_dtl_id")
        if dtl_id is None:
            continue

        item = agg[dtl_id]
        amt = rec.get("fund_disbursed_amount")
        if amt is not None:
            item["total_disbursed_amount"] += amt

        item["disbursement_count"] += 1

        vname = rec.get("vendor_name")
        if vname:
            item["vendors"].add(vname)

        vid = rec.get("vendor_id")
        if vid is not None:
            item["vendor_ids"].add(vid)

        ia = rec.get("implementing_agency")
        if ia:
            item["implementing_agencies"].add(ia)

        st = rec.get("work_status")
        if st:
            item["payment_statuses"].add(st)

        dt = rec.get("expenditure_date")
        if dt:
            curr = item["latest_expenditure_date"]
            if curr is None or dt > curr:
                item["latest_expenditure_date"] = dt

    result = {}
    for dtl_id, data in agg.items():
        result[dtl_id] = {
            "total_disbursed_amount": round(data["total_disbursed_amount"], 2),
            "disbursement_count": data["disbursement_count"],
            "vendor_count": len(data["vendors"]),
            "vendor_names": sorted(list(data["vendors"])),
            "vendor_ids": sorted(list(data["vendor_ids"])),
            "implementing_agencies": sorted(list(data["implementagencies"] if "implementagencies" in data else data["implementing_agencies"])),
            "latest_expenditure_date": data["latest_expenditure_date"],
            "payment_statuses": sorted(list(data["payment_statuses"])),
            "has_expenditure_evidence": True
        }
    return result


def build_canonical_work_master(
    recommended_raw: List[Dict[str, Any]],
    completed_raw: List[Dict[str, Any]],
    expenditure_raw: List[Dict[str, Any]] = None
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Builds authoritative canonical work master table by exact DTL_ID joins.

    Returns:
      (joined_master_records, join_audit_report)
    """
    comp_by_dtl: Dict[Any, Dict[str, Any]] = {}
    orphan_completed: List[Dict[str, Any]] = []

    for comp_item in completed_raw:
        c_rec = canonicalize_completed(comp_item)
        dtl = c_rec.get("work_recommendation_dtl_id")
        if dtl is not None:
            comp_by_dtl[dtl] = c_rec

    exp_by_dtl: Dict[Any, Dict[str, Any]] = {}
    if expenditure_raw:
        exp_by_dtl = aggregate_expenditure_by_dtl_id(expenditure_raw)

    master: List[Dict[str, Any]] = []
    matched_comp_ids = set()
    matched_exp_ids = set()

    for rec_item in recommended_raw:
        work = canonicalize_recommended(rec_item)
        dtl = work.get("work_recommendation_dtl_id")

        if dtl is not None and dtl in comp_by_dtl:
            comp_data = comp_by_dtl[dtl]
            matched_comp_ids.add(dtl)
            work["is_completed"] = True
            work["amount_completed"] = comp_data.get("amount_completed")
            work["completion_date"] = comp_data.get("completion_date")
            work["average_rating"] = comp_data.get("average_rating")
            work["has_completion_evidence"] = True
            # if unique_work_number wasn't in recommended (e.g. was NA), check completed
            if not work.get("unique_work_number") and comp_data.get("unique_work_number"):
                work["unique_work_number"] = comp_data.get("unique_work_number")
        else:
            work["is_completed"] = False
            work["amount_completed"] = None
            work["completion_date"] = None
            work["average_rating"] = None
            work["has_completion_evidence"] = False

        if dtl is not None and dtl in exp_by_dtl:
            exp_data = exp_by_dtl[dtl]
            matched_exp_ids.add(dtl)
            work["total_disbursed_amount"] = exp_data["total_disbursed_amount"]
            work["disbursement_count"] = exp_data["disbursement_count"]
            work["vendor_count"] = exp_data["vendor_count"]
            work["vendor_names"] = exp_data["vendor_names"]
            work["latest_expenditure_date"] = exp_data["latest_expenditure_date"]
            work["payment_statuses"] = exp_data["payment_statuses"]
            work["has_expenditure_evidence"] = True
        else:
            work["total_disbursed_amount"] = None
            work["disbursement_count"] = 0
            work["vendor_count"] = 0
            work["vendor_names"] = []
            work["latest_expenditure_date"] = None
            work["payment_statuses"] = []
            work["has_expenditure_evidence"] = False

        # Parse year bucket from recommendation_date if available
        rec_dt = work.get("recommendation_date")
        if rec_dt and len(rec_dt) >= 4:
            work["year"] = rec_dt[:4]
        else:
            work["year"] = "UNKNOWN"

        master.append(work)

    for dtl, c_rec in comp_by_dtl.items():
        if dtl not in matched_comp_ids:
            orphan_completed.append(c_rec)

    orphan_exp_count = len(exp_by_dtl) - len(matched_exp_ids)

    audit = {
        "recommended_total": len(recommended_raw),
        "completed_total": len(completed_raw),
        "expenditure_distinct_works": len(exp_by_dtl),
        "joined_master_count": len(master),
        "completed_matched_count": len(matched_comp_ids),
        "completed_orphan_count": len(orphan_completed),
        "expenditure_matched_count": len(matched_exp_ids),
        "expenditure_orphan_count": orphan_exp_count,
        "completed_match_rate_pct": round(len(matched_comp_ids) / len(comp_by_dtl) * 100, 2) if comp_by_dtl else 0.0,
        "expenditure_match_rate_pct": round(len(matched_exp_ids) / len(exp_by_dtl) * 100, 2) if exp_by_dtl else 0.0,
    }

    return master, audit
