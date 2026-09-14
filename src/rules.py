"""Compliance Hub — Deterministic Audit Rule Evaluation.

Provides objective, evidence-based compliance screening strictly using genuine
fields from canonical Government of India MoSPI records.

This module is conceptually separate from the 100-point analytical risk score.
Statuses:
- PASS
- WARNING
- NON-CONFORMING
- UNAVAILABLE
"""

from typing import Dict, Any, List, Optional
import pandas as pd


def evaluate_work_compliance(work_record: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluates project-level compliance checks strictly on genuine source fields.
    
    Returns a dictionary with overall summary and structured items.
    """
    if not work_record:
        return {
            "overall_status": "UNAVAILABLE",
            "passed_count": 0,
            "warning_count": 0,
            "non_conforming_count": 0,
            "unavailable_count": 5,
            "items": []
        }

    items = []

    # 1. Administrative Linkage Integrity
    dtl_id = work_record.get("work_recommendation_dtl_id")
    state = work_record.get("state")
    constituency = work_record.get("constituency") or work_record.get("district")
    mp_name = work_record.get("mp_name")
    cat = work_record.get("category")

    missing_core = []
    if not dtl_id or pd.isna(dtl_id):
        missing_core.append("DTL_ID")
    if not state or pd.isna(state) or str(state).strip().lower() in ("unknown", "unknown state"):
        missing_core.append("State")
    if not constituency or pd.isna(constituency) or str(constituency).strip().lower() in ("unknown", "unknown constituency"):
        missing_core.append("Constituency/District")
    if not mp_name or pd.isna(mp_name) or str(mp_name).strip().lower() in ("unknown",):
        missing_core.append("MP Name")
    if not cat or pd.isna(cat):
        missing_core.append("Category")

    if missing_core:
        items.append({
            "check_id": "ADMIN_LINKAGE",
            "title": "Administrative Linkage Integrity",
            "status": "NON-CONFORMING",
            "detail": f"Incomplete core administrative linkages: missing {', '.join(missing_core)}.",
            "field_evidence": f"Recorded fields: state={state}, constituency={constituency}, mp={mp_name}"
        })
    else:
        items.append({
            "check_id": "ADMIN_LINKAGE",
            "title": "Administrative Linkage Integrity",
            "status": "PASS",
            "detail": "All core administrative identifiers verified (State, Constituency, MP Name, Category).",
            "field_evidence": f"State: {state} | Constituency: {constituency} | MP: {mp_name} | Category: {cat}"
        })

    # 2. Implementing Authority Assignment
    impl_auth = work_record.get("implementing_authority") or work_record.get("ida_name_raw") or work_record.get("ida_name")
    if impl_auth and not pd.isna(impl_auth) and str(impl_auth).strip() not in ("", "UNSPECIFIED", "nan", "None"):
        items.append({
            "check_id": "IMPL_AUTHORITY",
            "title": "Implementing Authority Assignment",
            "status": "PASS",
            "detail": f"Designated implementing entity officially recorded in master registry.",
            "field_evidence": f"Authority: {str(impl_auth).strip()}"
        })
    else:
        items.append({
            "check_id": "IMPL_AUTHORITY",
            "title": "Implementing Authority Assignment",
            "status": "WARNING",
            "detail": "No implementing authority or department designated in official record.",
            "field_evidence": "implementing_authority field is missing or unspecified."
        })

    # 3. Financial Milestone Sequence Conformance
    rec_amt = work_record.get("amount_recommended")
    sanc_amt = work_record.get("amount_sanctioned")
    disb_amt = work_record.get("total_disbursed_amount")

    has_rec = rec_amt is not None and not pd.isna(rec_amt) and float(rec_amt) > 0
    has_sanc = sanc_amt is not None and not pd.isna(sanc_amt) and float(sanc_amt) > 0
    has_disb = disb_amt is not None and not pd.isna(disb_amt) and float(disb_amt) >= 0

    if not has_rec and not has_sanc:
        items.append({
            "check_id": "FINANCIAL_SEQUENCE",
            "title": "Financial Milestone Conformance",
            "status": "NON-CONFORMING",
            "detail": "Neither recommended amount nor sanctioned amount is recorded.",
            "field_evidence": "amount_recommended and amount_sanctioned are absent."
        })
    elif has_disb and has_sanc and float(disb_amt) > float(sanc_amt) * 1.05:
        over_pct = round((float(disb_amt) - float(sanc_amt)) / float(sanc_amt) * 100, 1)
        items.append({
            "check_id": "FINANCIAL_SEQUENCE",
            "title": "Financial Milestone Conformance",
            "status": "WARNING",
            "detail": f"Total disbursed amount exceeds recorded sanction by {over_pct}%. Requires reconciliation.",
            "field_evidence": f"Sanction: ₹{float(sanc_amt):,.0f} | Disbursed: ₹{float(disb_amt):,.0f}"
        })
    elif not has_disb:
        items.append({
            "check_id": "FINANCIAL_SEQUENCE",
            "title": "Financial Milestone Conformance",
            "status": "UNAVAILABLE",
            "detail": "UNAVAILABLE — disbursement/expenditure evidence not present in source dataset.",
            "field_evidence": "Disbursement records not yet linked or unavailable."
        })
    else:
        items.append({
            "check_id": "FINANCIAL_SEQUENCE",
            "title": "Financial Milestone Conformance",
            "status": "PASS",
            "detail": "Financial disbursements remain within authorized sanctioned allocation.",
            "field_evidence": f"Sanction: ₹{float(sanc_amt):,.0f} | Disbursed: ₹{float(disb_amt):,.0f}"
        })

    # 4. Chronological Milestone Conformance
    rec_dt = work_record.get("recommendation_date")
    sanc_dt = work_record.get("sanction_date")
    comp_dt = work_record.get("completion_date")

    has_rec_dt = rec_dt is not None and not pd.isna(rec_dt) and str(rec_dt).strip() not in ("", "nan")
    has_sanc_dt = sanc_dt is not None and not pd.isna(sanc_dt) and str(sanc_dt).strip() not in ("", "nan")
    has_comp_dt = comp_dt is not None and not pd.isna(comp_dt) and str(comp_dt).strip() not in ("", "nan")

    if not has_rec_dt and not has_sanc_dt and not has_comp_dt:
        items.append({
            "check_id": "CHRONOLOGY",
            "title": "Chronological Milestone Conformance",
            "status": "UNAVAILABLE",
            "detail": "UNAVAILABLE — milestone dates not present in source record.",
            "field_evidence": "No timestamp evidence available for milestone ordering."
        })
    else:
        chrono_issues = []
        if has_rec_dt and has_sanc_dt and str(sanc_dt) < str(rec_dt):
            chrono_issues.append("Sanction date precedes recommendation date.")
        if has_sanc_dt and has_comp_dt and str(comp_dt) < str(sanc_dt):
            chrono_issues.append("Completion date precedes sanction date.")

        if chrono_issues:
            items.append({
                "check_id": "CHRONOLOGY",
                "title": "Chronological Milestone Conformance",
                "status": "WARNING",
                "detail": f"Chronological inversion detected: {' '.join(chrono_issues)}",
                "field_evidence": f"Rec Date: {rec_dt} | Sanc Date: {sanc_dt} | Comp Date: {comp_dt}"
            })
        elif has_rec_dt and has_sanc_dt:
            items.append({
                "check_id": "CHRONOLOGY",
                "title": "Chronological Milestone Conformance",
                "status": "PASS",
                "detail": "Milestones follow an orderly administrative sequence.",
                "field_evidence": f"Rec Date: {rec_dt} | Sanc Date: {sanc_dt} | Comp Date: {comp_dt or 'In-progress'}"
            })
        else:
            items.append({
                "check_id": "CHRONOLOGY",
                "title": "Chronological Milestone Conformance",
                "status": "UNAVAILABLE",
                "detail": "UNAVAILABLE — required chronological milestone dates incomplete in source.",
                "field_evidence": f"Rec Date: {rec_dt or 'None'} | Sanc Date: {sanc_dt or 'None'}"
            })

    # 5. Completion Conformance
    is_comp = work_record.get("is_completed", False)
    comp_amt = work_record.get("amount_completed")
    has_comp_amt = comp_amt is not None and not pd.isna(comp_amt) and float(comp_amt) > 0

    if is_comp or (work_record.get("work_stage") and "completed" in str(work_record.get("work_stage")).lower()):
        if has_comp_amt or has_comp_dt:
            items.append({
                "check_id": "COMPLETION",
                "title": "Completion Conformance",
                "status": "PASS",
                "detail": "Work marked completed with verified completion record.",
                "field_evidence": f"Completion Date: {comp_dt or 'Recorded'} | Completed Amount: ₹{float(comp_amt or 0):,.0f}"
            })
        else:
            items.append({
                "check_id": "COMPLETION",
                "title": "Completion Conformance",
                "status": "WARNING",
                "detail": "Work marked as completed without recorded completion expenditure or date.",
                "field_evidence": "is_completed is True but completion financial values are unpopulated."
            })
    else:
        items.append({
            "check_id": "COMPLETION",
            "title": "Completion Conformance",
            "status": "UNAVAILABLE",
            "detail": "UNAVAILABLE — project is currently in-progress or completion record not submitted.",
            "field_evidence": f"Work stage: {work_record.get('work_stage') or 'In progress'}"
        })

    pass_cnt = sum(1 for i in items if i["status"] == "PASS")
    warn_cnt = sum(1 for i in items if i["status"] == "WARNING")
    nc_cnt = sum(1 for i in items if i["status"] == "NON-CONFORMING")
    unav_cnt = sum(1 for i in items if i["status"] == "UNAVAILABLE")

    if nc_cnt > 0:
        overall = "NON-CONFORMING"
    elif warn_cnt > 0:
        overall = "WARNING"
    elif pass_cnt > 0:
        overall = "PASS"
    else:
        overall = "UNAVAILABLE"

    return {
        "overall_status": overall,
        "passed_count": pass_cnt,
        "warning_count": warn_cnt,
        "non_conforming_count": nc_cnt,
        "unavailable_count": unav_cnt,
        "items": items
    }
