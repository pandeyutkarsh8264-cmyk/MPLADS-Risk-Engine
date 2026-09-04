"""Engine 1: Context-Aware Peer Benchmarking (Weight: 30%)

Implements the exact 5-step locked cohort hierarchy from the Complete Locked Build Spec:
  1) same district + same category + same year
  2) same district + same category
  3) same state + same category + same year
  4) same state + same category
  5) national + same category

Uses the first cohort meeting the minimum target of 10.
Uses robust statistics: median, IQR, empirical percentile rank, deviation ratios.
Never treats unavailable peer evidence as a zero score (returns None with coverage metadata).
"""

from typing import Dict, Any, List, Optional, Tuple
import math
from collections import defaultdict


COHORT_LEVELS = [
    (1, "district_category_year", ("district", "category", "year")),
    (2, "district_category", ("district", "category")),
    (3, "state_category_year", ("state", "category", "year")),
    (4, "state_category", ("state", "category")),
    (5, "national_category", ("category",))
]


class PeerBenchmarkEngine:
    """Pre-indexes works into the 5-step cohort hierarchy for O(1) peer retrieval."""

    def __init__(self, min_cohort_size: int = 10, iqr_fence: float = 1.5, extreme_fence: float = 3.0):
        self.min_cohort_size = min_cohort_size
        self.iqr_fence = iqr_fence
        self.extreme_fence = extreme_fence
        
        # Indexed cohort amount stores: level_idx -> key_tuple -> list of amounts
        self.cohort_indices: Dict[int, Dict[Tuple, List[float]]] = {
            1: defaultdict(list),
            2: defaultdict(list),
            3: defaultdict(list),
            4: defaultdict(list),
            5: defaultdict(list),
        }
        self.indexed_count = 0

    def _extract_keys(self, work: Dict[str, Any]) -> Dict[int, Optional[Tuple]]:
        """Extracts group keys for all 5 hierarchy levels."""
        cat = work.get("category")
        cat = work.get("category")
        if not cat or (isinstance(cat, float) and math.isnan(cat)):
            return {lvl: None for lvl in range(1, 6)}
        cat_s = str(cat).strip().lower()

        dist = work.get("district")
        dist_s = str(dist).strip().lower() if dist is not None and not (isinstance(dist, float) and math.isnan(dist)) else None

        st = work.get("state")
        st_s = str(st).strip().lower() if st is not None and not (isinstance(st, float) and math.isnan(st)) else None

        yr = work.get("year")
        yr_s = str(yr).strip() if yr is not None and yr != "UNKNOWN" and not (isinstance(yr, float) and math.isnan(yr)) else None

        keys = {}
        # Level 1: district + category + year
        keys[1] = (dist_s, cat_s, yr_s) if dist_s and yr_s else None
        # Level 2: district + category
        keys[2] = (dist_s, cat_s) if dist_s else None
        # Level 3: state + category + year
        keys[3] = (st_s, cat_s, yr_s) if st_s and yr_s else None
        # Level 4: state + category
        keys[4] = (st_s, cat_s) if st_s else None
        # Level 5: national + category
        keys[5] = (cat_s,)
        return keys

    def fit(self, works: List[Dict[str, Any]]) -> "PeerBenchmarkEngine":
        """Indexes an entire corpus of canonical works into peer cohorts."""
        self.indexed_count = 0
        for w in works:
            amt = w.get("amount_recommended")
            if amt is None or amt <= 0:
                continue

            keys = self._extract_keys(w)
            for lvl, key in keys.items():
                if key is not None:
                    self.cohort_indices[lvl][key].append(amt)
            self.indexed_count += 1

        # Sort all cohort amount lists for efficient quantile calculations
        for lvl in self.cohort_indices:
            for key in self.cohort_indices[lvl]:
                self.cohort_indices[lvl][key].sort()

        return self

    def _compute_robust_stats(self, amounts: List[float]) -> Dict[str, float]:
        """Calculates Q1, median, Q3, and IQR from a sorted list of values."""
        n = len(amounts)
        if n == 0:
            return {"median": 0.0, "q1": 0.0, "q3": 0.0, "iqr": 0.0}

        def get_percentile(p: float) -> float:
            idx = p * (n - 1)
            lower = int(math.floor(idx))
            upper = int(math.ceil(idx))
            if lower == upper:
                return amounts[lower]
            return amounts[lower] + (idx - lower) * (amounts[upper] - amounts[lower])

        q1 = get_percentile(0.25)
        med = get_percentile(0.50)
        q3 = get_percentile(0.75)
        iqr = max(0.0, q3 - q1)

        return {
            "median": round(med, 2),
            "q1": round(q1, 2),
            "q3": round(q3, 2),
            "iqr": round(iqr, 2)
        }

    def evaluate_work(self, work: Dict[str, Any]) -> Dict[str, Any]:
        """Scores a single work against the 5-step peer hierarchy.

        Returns:
          dict with:
            score (0-100 or None if insufficient peers)
            cohort_level (1-5 or None)
            cohort_level_name (str)
            cohort_size (int)
            peer_median, peer_q1, peer_q3, peer_iqr (floats)
            percentile_rank (0-100 float)
            deviation_ratio (float)
            reason_codes (list[str])
            evidence (str)
            coverage (str: "full", "fallback_step_X", "insufficient_peers", "missing_amount")
        """
        amt = work.get("amount_recommended")
        if amt is None or amt <= 0:
            return {
                "score": None,
                "available": False,
                "cohort_level": None,
                "cohort_level_name": None,
                "cohort_size": 0,
                "peer_median": None,
                "peer_q1": None,
                "peer_q3": None,
                "peer_iqr": None,
                "percentile_rank": None,
                "deviation_ratio": None,
                "reason_codes": ["MISSING_RECOMMENDED_AMOUNT"],
                "evidence": "Work lacks a valid positive recommended amount for peer comparison.",
                "coverage": "missing_amount"
            }

        keys = self._extract_keys(work)
        
        selected_level = None
        selected_level_name = None
        selected_cohort = None

        # Traverse the 5-step hierarchy strictly in order
        for lvl, lvl_name, _ in COHORT_LEVELS:
            k = keys.get(lvl)
            if k is not None and k in self.cohort_indices[lvl]:
                cohort = self.cohort_indices[lvl][k]
                if len(cohort) >= self.min_cohort_size:
                    selected_level = lvl
                    selected_level_name = lvl_name
                    selected_cohort = cohort
                    break

        # If no cohort met minimum target of 10
        if selected_cohort is None:
            # Check largest available for reporting
            max_size = 0
            for lvl in range(1, 6):
                k = keys.get(lvl)
                if k and k in self.cohort_indices[lvl]:
                    max_size = max(max_size, len(self.cohort_indices[lvl][k]))
            return {
                "score": None,
                "available": False,
                "cohort_level": None,
                "cohort_level_name": None,
                "cohort_size": max_size,
                "peer_median": None,
                "peer_q1": None,
                "peer_q3": None,
                "peer_iqr": None,
                "percentile_rank": None,
                "deviation_ratio": None,
                "reason_codes": ["PEER_INSUFFICIENT_COHORT"],
                "evidence": f"No cohort met minimum target of {self.min_cohort_size} peers (largest available had {max_size}).",
                "coverage": "insufficient_peers"
            }

        # Calculate robust cohort statistics
        stats = self._compute_robust_stats(selected_cohort)
        med = stats["median"]
        q1 = stats["q1"]
        q3 = stats["q3"]
        iqr = stats["iqr"]
        n = len(selected_cohort)

        # Percentile rank
        less = sum(1 for x in selected_cohort if x < amt)
        equal = sum(1 for x in selected_cohort if x == amt)
        pct_rank = round(((less + 0.5 * equal) / n) * 100.0, 2)

        # Deviation ratio vs median
        if med > 0:
            dev_ratio = round(amt / med, 2)
        else:
            dev_ratio = 1.0

        # Calculate fences
        f1_5 = q3 + self.iqr_fence * iqr
        f3_0 = q3 + self.extreme_fence * iqr

        reason_codes = []
        
        # Add cohort level tag
        reason_codes.append(f"COHORT_STEP_{selected_level}_{selected_level_name.upper()}")

        # Score calculation
        score = 0.0
        if iqr > 0:
            if amt <= q3:
                # Within IQR or lower: 0 - 25 scale
                if amt <= q1:
                    score = max(0.0, 10.0 * (amt / q1)) if q1 > 0 else 5.0
                else:
                    score = 10.0 + 15.0 * ((amt - q1) / iqr)
            elif amt <= f1_5:
                # Mild deviation (Q3 to Q3 + 1.5*IQR): 25 - 55 scale
                fraction = (amt - q3) / (f1_5 - q3) if f1_5 > q3 else 0.0
                score = 25.0 + 30.0 * fraction
                reason_codes.append("PEER_ELEVATED_AMOUNT")
            elif amt <= f3_0:
                # Moderate/High outlier (1.5*IQR to 3.0*IQR): 55 - 80 scale
                fraction = (amt - f1_5) / (f3_0 - f1_5) if f3_0 > f1_5 else 0.0
                score = 55.0 + 25.0 * fraction
                reason_codes.append("PEER_OUTLIER_1_5X_IQR")
            else:
                # Extreme outlier (> 3.0*IQR): 80 - 100 scale
                excess = (amt - f3_0) / (iqr if iqr > 0 else 1.0)
                score = min(100.0, 80.0 + 20.0 * (1.0 - math.exp(-excess / 2.0)))
                reason_codes.append("PEER_EXTREME_OUTLIER_3X_IQR")
        else:
            # IQR is 0 (homogeneous cohort)
            if amt == med:
                score = 0.0
            elif amt < med:
                score = 5.0
            else:
                ratio = amt / med if med > 0 else 1.0
                if ratio > 3.0:
                    score = 90.0
                    reason_codes.append("PEER_EXTREME_HOMOGENEOUS_DEVIATION")
                elif ratio > 1.5:
                    score = 65.0
                    reason_codes.append("PEER_MODERATE_HOMOGENEOUS_DEVIATION")
                else:
                    score = 35.0

        if pct_rank >= 95.0:
            reason_codes.append("PEER_TOP_5_PERCENTILE")
        elif pct_rank >= 90.0:
            reason_codes.append("PEER_TOP_10_PERCENTILE")

        score = round(min(100.0, max(0.0, score)), 2)

        # Build coverage tag
        coverage = "full" if selected_level == 1 else f"fallback_step_{selected_level}"

        # Human-readable evidence narrative
        cat_disp = work.get("category", "Unknown")
        loc_disp = work.get("district") or work.get("state") or "National"
        evidence = (
            f"Recommended amount ₹{amt:,.0f} evaluated at Level {selected_level} ({selected_level_name}, n={n}). "
            f"Cohort median: ₹{med:,.0f}, IQR: ₹{iqr:,.0f} (Q1: ₹{q1:,.0f}, Q3: ₹{q3:,.0f}). "
            f"Work is at {pct_rank:.1f}th percentile ({dev_ratio:.1f}x peer median)."
        )

        return {
            "score": score,
            "available": True,
            "cohort_level": selected_level,
            "cohort_level_name": selected_level_name,
            "cohort_size": n,
            "peer_median": med,
            "peer_q1": q1,
            "peer_q3": q3,
            "peer_iqr": iqr,
            "percentile_rank": pct_rank,
            "deviation_ratio": dev_ratio,
            "reason_codes": reason_codes,
            "evidence": evidence,
            "coverage": coverage
        }
