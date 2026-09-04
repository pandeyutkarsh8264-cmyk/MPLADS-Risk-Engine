"""Engine 2: Statistical Outliers (Weight: 25%)

Primary deterministic robust methods:
- Median Absolute Deviation (MAD) & Modified Z-scores
- Interquartile Range (IQR) fences
- Zero-dispersion safety: features with MAD/IQR = 0 return neutral/no-anomaly scores
- Genuinely available numeric features only
- Missing features are omitted and reflected in coverage (never treated as zero)
- Strictly avoids Isolation Forest as primary, Benford's Law, fiscal bursts, forecasting.
"""

from typing import Dict, Any, List, Optional, Tuple
import math
from datetime import datetime


def _parse_date(date_str: Optional[str]) -> Optional[datetime]:
    if not date_str or not isinstance(date_str, str):
        return None
    for fmt in ("%Y-%m-%d", "%d-%b-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    return None


def _clean_float(val: Any) -> Optional[float]:
    """Sanitizes floats against None, NaN, and Inf."""
    if val is None:
        return None
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    except (ValueError, TypeError):
        return None


class StatisticalOutlierEngine:
    """Robust statistical outlier detection engine using Median and MAD.

    Follows locked build specification:
    - 25% weight in fusion
    - Evaluates available numeric features
    - Zero-dispersion safety (constant baseline does not spike score)
    - Missing features are omitted from composite (never treated as 0)
    """

    FEATURE_DEFS = [
        ("amount_recommended", "Recommended Cost", True),
        ("amount_sanctioned", "Sanctioned Cost", True),
        ("sanction_to_rec_ratio", "Sanction to Recommended Ratio", False),
        ("sanction_delay_days", "Sanction Delay Days", False),
        ("completed_cost_ratio", "Completed to Sanctioned Ratio", False),
        ("disbursed_to_sanction_ratio", "Disbursed to Sanctioned Ratio", False)
    ]

    def __init__(
        self,
        z_mod_threshold: float = 3.5,
        extreme_z_threshold: float = 6.0,
        zero_dispersion_threshold: float = 1e-6
    ):
        self.z_mod_threshold = z_mod_threshold
        self.extreme_z_threshold = extreme_z_threshold
        self.zero_dispersion_threshold = zero_dispersion_threshold
        self.feature_stats: Dict[str, Dict[str, float]] = {}
        self.fitted = False

    def _extract_work_features(self, work: Dict[str, Any]) -> Dict[str, Optional[float]]:
        """Extracts valid numeric feature values for a work. Returns None for unavailable features."""
        feats = {}

        # 1. amount_recommended
        rec_amt = _clean_float(work.get("amount_recommended"))
        feats["amount_recommended"] = rec_amt if rec_amt is not None and rec_amt > 0 else None

        # 2. amount_sanctioned
        sanc_amt = _clean_float(work.get("amount_sanctioned"))
        feats["amount_sanctioned"] = sanc_amt if sanc_amt is not None and sanc_amt > 0 else None

        # 3. sanction_to_rec_ratio
        if feats["amount_recommended"] and feats["amount_sanctioned"]:
            feats["sanction_to_rec_ratio"] = round(feats["amount_sanctioned"] / feats["amount_recommended"], 4)
        else:
            feats["sanction_to_rec_ratio"] = None

        # 4. sanction_delay_days
        rec_d = _parse_date(work.get("recommendation_date"))
        sanc_d = _parse_date(work.get("sanction_date"))
        if rec_d and sanc_d:
            delay = (sanc_d - rec_d).days
            feats["sanction_delay_days"] = float(max(0, delay))
        else:
            feats["sanction_delay_days"] = None

        # 5. completed_cost_ratio
        comp_amt = _clean_float(work.get("amount_completed"))
        if comp_amt is not None and feats["amount_sanctioned"] and feats["amount_sanctioned"] > 0:
            feats["completed_cost_ratio"] = round(comp_amt / feats["amount_sanctioned"], 4)
        else:
            feats["completed_cost_ratio"] = None

        # 6. disbursed_to_sanction_ratio
        disb_amt = _clean_float(work.get("total_disbursed_amount"))
        if disb_amt is not None and feats["amount_sanctioned"] and feats["amount_sanctioned"] > 0:
            feats["disbursed_to_sanction_ratio"] = round(disb_amt / feats["amount_sanctioned"], 4)
        else:
            feats["disbursed_to_sanction_ratio"] = None

        return feats

    def fit(self, works: List[Dict[str, Any]]) -> "StatisticalOutlierEngine":
        """Calculates population baseline median and MAD for all available features."""
        feat_values: Dict[str, List[float]] = {fname: [] for fname, _, _ in self.FEATURE_DEFS}

        for w in works:
            w_feats = self._extract_work_features(w)
            for fname, val in w_feats.items():
                if val is not None and not math.isnan(val) and not math.isinf(val):
                    feat_values[fname].append(val)

        for fname, vals in feat_values.items():
            if len(vals) < 10:
                continue

            vals.sort()
            n = len(vals)
            med = vals[n // 2] if n % 2 != 0 else (vals[n // 2 - 1] + vals[n // 2]) / 2.0

            # Median Absolute Deviation (MAD)
            devs = [abs(x - med) for x in vals]
            devs.sort()
            mad = devs[n // 2] if n % 2 != 0 else (devs[n // 2 - 1] + devs[n // 2]) / 2.0

            # Interquartile Range (IQR)
            q1 = vals[n // 4]
            q3 = vals[3 * n // 4]
            iqr = max(0.0, q3 - q1)

            self.feature_stats[fname] = {
                "count": n,
                "median": med,
                "mad": mad,
                "q1": q1,
                "q3": q3,
                "iqr": iqr
            }

        self.fitted = True
        return self

    def _score_single_feature(self, fname: str, val: float) -> Tuple[float, float, List[str], str]:
        """Calculates Modified Z-score and 0-100 anomaly sub-score for one feature with zero-dispersion safety."""
        stats = self.feature_stats[fname]
        med = stats["median"]
        mad = stats["mad"]
        iqr = stats["iqr"]

        # Zero-dispersion safety check
        if mad <= self.zero_dispersion_threshold and iqr <= self.zero_dispersion_threshold:
            # Constant or near-constant population baseline: safely return neutral/no-anomaly
            evidence_str = f"{fname}: constant baseline (val={val:,.2f}, median={med:,.2f}, zero dispersion), treated as neutral"
            return 0.0, 0.0, [], evidence_str

        # Calculate Modified Z-score using robust dispersion
        if mad > self.zero_dispersion_threshold:
            mod_z = 0.6745 * abs(val - med) / mad
        elif iqr > self.zero_dispersion_threshold:
            mod_z = abs(val - med) / (0.7413 * iqr)
        else:
            mod_z = 0.0

        # Map to 0-100 sub-score
        if mod_z <= 2.0:
            sub_score = 12.5 * mod_z  # 0 to 25
        elif mod_z <= self.z_mod_threshold:
            # 2.0 to 3.5 -> 25 to 55
            sub_score = 25.0 + 30.0 * ((mod_z - 2.0) / (self.z_mod_threshold - 2.0))
        elif mod_z <= self.extreme_z_threshold:
            # 3.5 to 6.0 -> 55 to 85
            sub_score = 55.0 + 30.0 * ((mod_z - self.z_mod_threshold) / (self.extreme_z_threshold - self.z_mod_threshold))
        else:
            # > 6.0 -> 85 to 100
            excess = mod_z - self.extreme_z_threshold
            sub_score = min(100.0, 85.0 + 15.0 * (1.0 - math.exp(-excess / 3.0)))

        reason_codes = []
        is_high = val > med
        direction = "HIGH" if is_high else "LOW"
        fname_upper = fname.upper()

        if mod_z >= self.extreme_z_threshold:
            reason_codes.append(f"STAT_EXTREME_OUTLIER_{direction}_{fname_upper}")
        elif mod_z >= self.z_mod_threshold:
            reason_codes.append(f"STAT_OUTLIER_{direction}_{fname_upper}")

        evidence_str = f"{fname}: val={val:,.2f} vs median={med:,.2f} (mod_z={mod_z:.2f}, score={sub_score:.1f})"

        return round(sub_score, 2), round(mod_z, 2), reason_codes, evidence_str

    def evaluate_work(self, work: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluates a work on all genuinely available features.

        Missing features are omitted and reflected in coverage (never treated as zero).
        Zero-dispersion features safely evaluate to neutral.
        """
        w_feats = self._extract_work_features(work)

        feature_scores: Dict[str, float] = {}
        feature_zscores: Dict[str, float] = {}
        all_reason_codes: List[str] = []
        evidence_lines: List[str] = []

        used_features = []
        omitted_features = []

        for fname, _, _ in self.FEATURE_DEFS:
            val = w_feats.get(fname)
            if val is not None and not math.isnan(val) and fname in self.feature_stats:
                sub_score, mod_z, r_codes, ev_str = self._score_single_feature(fname, val)
                feature_scores[fname] = sub_score
                feature_zscores[fname] = mod_z
                all_reason_codes.extend(r_codes)
                evidence_lines.append(ev_str)
                used_features.append(fname)
            else:
                omitted_features.append(fname)

        if not used_features:
            return {
                "score": None,
                "available": False,
                "feature_scores": {},
                "feature_zscores": {},
                "features_available": 0,
                "features_total": len(self.FEATURE_DEFS),
                "used_features": [],
                "omitted_features": omitted_features,
                "reason_codes": ["STAT_NO_FEATURES_AVAILABLE"],
                "evidence": "No valid numeric features available for statistical outlier evaluation.",
                "coverage": "no_features"
            }

        # Availability-normalized aggregation: mean of available feature scores
        composite_score = round(sum(feature_scores.values()) / len(feature_scores), 2)
        composite_score = min(100.0, max(0.0, composite_score))

        coverage_ratio = len(used_features) / len(self.FEATURE_DEFS)
        if coverage_ratio >= 0.8:
            cov_label = "full"
        elif coverage_ratio >= 0.5:
            cov_label = "partial_high"
        else:
            cov_label = "partial_low"

        evidence_text = (
            f"Evaluated on {len(used_features)}/{len(self.FEATURE_DEFS)} available features "
            f"(composite score: {composite_score:.1f}). " + "; ".join(evidence_lines)
        )

        return {
            "score": composite_score,
            "available": True,
            "feature_scores": feature_scores,
            "feature_zscores": feature_zscores,
            "features_available": len(used_features),
            "features_total": len(self.FEATURE_DEFS),
            "used_features": used_features,
            "omitted_features": omitted_features,
            "reason_codes": all_reason_codes,
            "evidence": evidence_text,
            "coverage": cov_label
        }
