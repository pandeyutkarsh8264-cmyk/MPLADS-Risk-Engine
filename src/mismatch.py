"""Engine 3: Financial–Execution Mismatch (Weight: 30%)

Strictly implements the locked 3-tier evidence hierarchy with exact confidence labels:
  - Level 1 Proxy: Status + Unsanctioned Timelines (Confidence: LOW)
  - Level 1 Observed Financial: Joined Completed/Expenditure Amounts vs Sanctions (Confidence: MEDIUM)
  - Level 2 Time-Based: Time + Money, Peer-comparative execution durations (Confidence: HIGH)
  - Level 3 Physical: Actual Physical Progress vs Money (Confidence: VERY HIGH)
    -> Strictly UNAVAILABLE in source data; NEVER fabricated or inferred.

Uses observed work-level evidence only via validated DTL_ID join.
All heuristic threshold defaults are tunable prototype parameters, NOT locked constants.
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import math
from collections import defaultdict


def _parse_iso_or_source_date(date_val: Optional[str]) -> Optional[datetime]:
    if not date_val or not isinstance(date_val, str):
        return None
    for fmt in ("%Y-%m-%d", "%d-%b-%Y", "%b %d, %Y %I:%M:%S %p", "%d/%m/%Y"):
        try:
            return datetime.strptime(date_val.strip(), fmt)
        except ValueError:
            continue
    return None


class FinancialExecutionMismatchEngine:
    """Evaluates financial vs execution timeline and status alignment using robust peer-comparative durations and observed financial realization."""

    def __init__(
        self,
        cost_overrun_threshold: float = 0.10,          # Tunable prototype heuristic: 10% overrun
        extreme_overrun_threshold: float = 0.50,        # Tunable prototype heuristic: 50% severe overrun
        sanction_rec_gap_threshold: float = 0.25,       # Tunable prototype heuristic: 25% discrepancy
        disbursement_overrun_threshold: float = 0.20,   # Tunable prototype heuristic: 20% disbursement overrun
        prolonged_pending_days: int = 180,              # Tunable prototype heuristic: 180 days pending
        large_unprocessed_amount: float = 5000000.0,    # Tunable prototype heuristic: ₹50 Lakh
        fast_completion_days: int = 3,                  # Tunable prototype heuristic: 3 days
        stalled_execution_days: int = 365,              # Tunable prototype heuristic: 365 days stalled
        reference_date: Optional[str] = "2026-09-03"
    ):
        self.cost_overrun_threshold = cost_overrun_threshold
        self.extreme_overrun_threshold = extreme_overrun_threshold
        self.sanction_rec_gap_threshold = sanction_rec_gap_threshold
        self.disbursement_overrun_threshold = disbursement_overrun_threshold
        self.prolonged_pending_days = prolonged_pending_days
        self.large_unprocessed_amount = large_unprocessed_amount
        self.fast_completion_days = fast_completion_days
        self.stalled_execution_days = stalled_execution_days
        self.reference_date = _parse_iso_or_source_date(reference_date) or datetime(2026, 9, 3)

        # Peer completion duration distributions by category: cat -> dict of stats
        self.peer_durations: Dict[str, Dict[str, float]] = {}

    def fit_peer_durations(self, works: List[Dict[str, Any]]) -> "FinancialExecutionMismatchEngine":
        """Calculates robust peer duration distributions (median, IQR) by work category from completed works."""
        cat_durations: Dict[str, List[float]] = defaultdict(list)

        for w in works:
            if not w.get("is_completed"):
                continue
            sanc_d = _parse_iso_or_source_date(w.get("sanction_date"))
            comp_d = _parse_iso_or_source_date(w.get("completion_date"))
            if sanc_d and comp_d and comp_d >= sanc_d:
                cat = str(w.get("category") or "unknown").strip().lower()
                duration = float((comp_d - sanc_d).days)
                cat_durations[cat].append(duration)

        for cat, durs in cat_durations.items():
            if len(durs) >= 10:
                durs.sort()
                n = len(durs)
                med = durs[n // 2]
                q1 = durs[n // 4]
                q3 = durs[3 * n // 4]
                self.peer_durations[cat] = {
                    "count": n,
                    "median": med,
                    "q1": q1,
                    "q3": q3,
                    "iqr": max(0.0, q3 - q1)
                }

        return self

    def evaluate_work(self, work: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluates a canonical master work record for financial-execution mismatch.

        Returns:
          score: 0-100 float or None
          confidence_level: 1, 2, or None
          confidence_label: "LOW", "MEDIUM", "HIGH", or "VERY HIGH"
          signals: list of detected mismatch signals
          reason_codes: list of machine-readable reason codes
          evidence: human-readable explanation
          coverage: coverage metadata
        """
        def _clean_num(val):
            if val is None:
                return None
            try:
                f = float(val)
                return None if math.isnan(f) else f
            except (ValueError, TypeError):
                return None

        rec_amt = _clean_num(work.get("amount_recommended"))
        sanc_amt = _clean_num(work.get("amount_sanctioned"))
        comp_amt = _clean_num(work.get("amount_completed"))
        disb_amt = _clean_num(work.get("total_disbursed_amount"))

        rec_d = _parse_iso_or_source_date(work.get("recommendation_date"))
        sanc_d = _parse_iso_or_source_date(work.get("sanction_date"))
        comp_d = _parse_iso_or_source_date(work.get("completion_date"))

        stage = str(work.get("work_stage") or "").strip()
        cat = str(work.get("category") or "").strip().lower()
        is_purchase = any(kw in cat for kw in ("purchase", "procurement", "supply", "equipment"))

        signals = []
        reason_codes = []

        # =====================================================================
        # TIER 1: LEVEL 1 PROXY (Confidence: LOW)
        # Observed status and un-sanctioned milestone delays
        # =====================================================================
        l1_proxy_signals = []
        l1_proxy_score = 0.0

        # P1: Unsanctioned or pending stage with prolonged delay
        if rec_d and not sanc_d:
            delay = (self.reference_date - rec_d).days
            if delay > self.prolonged_pending_days:
                l1_proxy_signals.append(f"Pending sanction for {delay} days (> {self.prolonged_pending_days} days)")
                l1_proxy_score += min(35.0, 15.0 + (delay - self.prolonged_pending_days) / 30.0 * 3.0)
                reason_codes.append("MISMATCH_L1_PROLONGED_PENDING_SANCTION")

        # P2: Substantial recommended amount stalled at initial stage
        if rec_amt and rec_amt >= self.large_unprocessed_amount and (not sanc_amt or sanc_amt == 0.0):
            l1_proxy_signals.append(f"Large amount (₹{rec_amt:,.0f}) remaining unsanctioned")
            l1_proxy_score += 25.0
            reason_codes.append("MISMATCH_L1_LARGE_AMOUNT_UNPROCESSED")

        # =====================================================================
        # TIER 1: LEVEL 1 OBSERVED FINANCIAL (Confidence: MEDIUM)
        # Evaluated via validated exact DTL_ID joins to completed and expenditure
        # =====================================================================
        l1_fin_signals = []
        l1_fin_score = 0.0
        has_l1_fin = False

        # F1: Sanction vs Recommended gap discrepancy
        if rec_amt and sanc_amt and rec_amt > 0:
            has_l1_fin = True
            gap_ratio = abs(sanc_amt - rec_amt) / rec_amt
            if gap_ratio > self.sanction_rec_gap_threshold:
                l1_fin_signals.append(f"Sanctioned amount (₹{sanc_amt:,.0f}) deviates {gap_ratio*100:.1f}% from recommended (₹{rec_amt:,.0f})")
                l1_fin_score += min(40.0, gap_ratio * 50.0)
                reason_codes.append("MISMATCH_L1_SANCTION_RECOMMENDED_GAP")

        # F2: Completed amount vs Sanctioned amount cost overrun
        if comp_amt is not None and sanc_amt and sanc_amt > 0:
            has_l1_fin = True
            overrun_ratio = (comp_amt - sanc_amt) / sanc_amt
            if overrun_ratio > self.extreme_overrun_threshold:
                l1_fin_signals.append(f"Severe completion cost overrun: ₹{comp_amt:,.0f} vs sanctioned ₹{sanc_amt:,.0f} (+{overrun_ratio*100:.1f}%)")
                l1_fin_score += 75.0
                reason_codes.append("MISMATCH_L1_EXTREME_COST_OVERRUN")
            elif overrun_ratio > self.cost_overrun_threshold:
                l1_fin_signals.append(f"Completion cost overrun: ₹{comp_amt:,.0f} vs sanctioned ₹{sanc_amt:,.0f} (+{overrun_ratio*100:.1f}%)")
                l1_fin_score += 45.0
                reason_codes.append("MISMATCH_L1_COST_OVERRUN")

        # F3: Total disbursed expenditure vs Sanctioned amount
        if disb_amt is not None and sanc_amt and sanc_amt > 0:
            has_l1_fin = True
            disb_ratio = disb_amt / sanc_amt
            if disb_ratio > (1.0 + self.disbursement_overrun_threshold):
                l1_fin_signals.append(f"Vendor disbursements (₹{disb_amt:,.0f}) exceed sanction (₹{sanc_amt:,.0f}) by {(disb_ratio-1.0)*100:.1f}%")
                l1_fin_score += min(70.0, 35.0 + (disb_ratio - 1.0 - self.disbursement_overrun_threshold) * 80.0)
                reason_codes.append("MISMATCH_L1_DISBURSEMENT_EXCEEDS_SANCTION")

        # F4: High disbursement with incomplete or early work stage
        if disb_amt and sanc_amt and (disb_amt >= sanc_amt * 0.90):
            has_l1_fin = True
            if not work.get("is_completed") and stage in ("Pending for Sanction", "Action Pending", "Physical Inspection"):
                l1_fin_signals.append(f"Disbursed {disb_amt/sanc_amt*100:.0f}% of funds while stage is '{stage}' without completion")
                l1_fin_score += 55.0
                reason_codes.append("MISMATCH_L1_HIGH_DISBURSEMENT_EARLY_STAGE")

        # =====================================================================
        # TIER 2: LEVEL 2 TIME-BASED (Confidence: HIGH)
        # Observed duration compared with peer completion duration distributions
        # =====================================================================
        l2_time_signals = []
        l2_time_score = 0.0
        has_l2_time = False

        peer_stat = self.peer_durations.get(cat)

        # T1: Impossibly fast completion relative to peers / threshold
        if sanc_d and comp_d and not is_purchase:
            has_l2_time = True
            duration_days = (comp_d - sanc_d).days
            
            # Robust peer-comparative check if peer distributions available
            is_fast = False
            if peer_stat and peer_stat["median"] > 30:
                fast_cutoff = max(self.fast_completion_days, peer_stat["median"] * 0.05)
                if duration_days < fast_cutoff:
                    is_fast = True
            elif duration_days < self.fast_completion_days:
                is_fast = True

            if is_fast:
                l2_time_signals.append(f"Impossibly rapid completion in {duration_days} days (sanction to completion)")
                l2_time_score += 80.0
                reason_codes.append("MISMATCH_L2_IMPOSSIBLY_FAST_COMPLETION")

        # T2: Prolonged execution: sanctioned with zero completion and zero disbursements
        if sanc_d and not comp_d:
            has_l2_time = True
            elapsed = (self.reference_date - sanc_d).days
            stalled_cutoff = max(self.stalled_execution_days, peer_stat["median"] * 2.0) if peer_stat else self.stalled_execution_days
            
            if elapsed > stalled_cutoff:
                if not disb_amt or disb_amt == 0.0:
                    l2_time_signals.append(f"Stalled project: {elapsed} days elapsed since sanction with zero disbursements")
                    l2_time_score += min(60.0, 30.0 + (elapsed - stalled_cutoff) / 60.0 * 10.0)
                    reason_codes.append("MISMATCH_L2_STALLED_EXECUTION_NO_DISBURSEMENT")

        # T3: Timeline inversion anomaly (completion date strictly precedes sanction date)
        if sanc_d and comp_d and comp_d < sanc_d:
            has_l2_time = True
            inversion_days = (sanc_d - comp_d).days
            l2_time_signals.append(f"Timeline inversion: completed date ({comp_d.strftime('%Y-%m-%d')}) precedes sanction date ({sanc_d.strftime('%Y-%m-%d')}) by {inversion_days} days")
            l2_time_score += 85.0
            reason_codes.append("MISMATCH_L2_TIMELINE_INVERSION")

        # =====================================================================
        # TIER 3: LEVEL 3 PHYSICAL PROGRESS (Confidence: VERY HIGH)
        # =====================================================================
        # Strictly UNAVAILABLE in source data; NEVER fabricated or inferred
        reason_codes.append("MISMATCH_L3_PHYSICAL_PROGRESS_UNAVAILABLE")

        # =====================================================================
        # COMPOSITE SCORE & CONFIDENCE RESOLUTION
        # =====================================================================
        has_execution_data = (
            has_l2_time 
            or (comp_amt is not None) 
            or (disb_amt is not None)
            or (len(l1_proxy_signals) > 0)
        )

        if not has_execution_data:
            return {
                "score": None,
                "available": False,
                "confidence_level": None,
                "confidence_label": "NONE",
                "signals": [],
                "reason_codes": reason_codes + ["MISMATCH_EXECUTION_DATA_UNAVAILABLE"],
                "evidence": "Financial-execution mismatch unavailable: work lacks sanction, completion, and expenditure evidence.",
                "coverage": "unavailable",
                "level_3_status": "UNAVAILABLE_IN_SOURCE"
            }

        if l2_time_score > 0 and l1_fin_score > 0:
            active_confidence = "HIGH"
            raw_score = min(100.0, max(l2_time_score, l1_fin_score) + 0.25 * min(l2_time_score, l1_fin_score))
        elif l2_time_score > 0:
            active_confidence = "HIGH"
            raw_score = l2_time_score
        elif l1_fin_score > 0:
            active_confidence = "HIGH" if has_l2_time else "MEDIUM"
            raw_score = l1_fin_score
        elif l1_proxy_score > 0:
            active_confidence = "LOW"
            raw_score = l1_proxy_score
        else:
            active_confidence = "HIGH" if has_l2_time else ("MEDIUM" if has_l1_fin else "LOW")
            raw_score = 0.0

        final_score = round(min(100.0, max(0.0, raw_score)), 2)

        # Collect all active signal strings
        all_signals = l1_proxy_signals + l1_fin_signals + l2_time_signals
        if not all_signals:
            final_score = 0.0
            evidence = "No financial, temporal, or status mismatches detected. Work milestones align."
            coverage = "no_mismatch_detected"
        else:
            evidence = f"[{active_confidence} CONFIDENCE] " + "; ".join(all_signals)
            coverage = f"active_tier_{active_confidence.lower()}"

        return {
            "score": final_score,
            "available": True,
            "confidence_level": 2 if active_confidence == "HIGH" else (1 if active_confidence == "MEDIUM" else 1),
            "confidence_label": active_confidence,
            "signals": all_signals,
            "reason_codes": reason_codes,
            "evidence": evidence,
            "coverage": coverage,
            "level_3_status": "UNAVAILABLE_IN_SOURCE"
        }
