# MPLADS Risk Intelligence & Investigation Engine — Final Submission Checklist

> **SIH26102 Implementation**  
> Government of India Ministry of Statistics and Programme Implementation (MoSPI)  
> 18th Lok Sabha Screening & Multimodal Evidence Fusion Platform  
> **Final Status**: **FROZEN • VERIFIED • SUBMISSION READY**

---

## 1. Executive Build Status Summary

| Item | Requirement | Verification Status | Notes |
| :--- | :--- | :---: | :--- |
| **Codebase State** | Frozen (No new features or UI refactoring) | ✅ **LOCKED** | Analytical logic, weights, bands, and schema frozen |
| **Test Suite** | 26/26 unit tests passing | ✅ **PASSED** | `26 passed in 30.30s` (`pytest tests/ -v`) |
| **Port Status** | Clean shutdown, port 8501 unallocated | ✅ **VERIFIED** | Verified via `Get-NetTCPConnection` |
| **Authoritative Key** | Exact `WORK_RECOMMENDATION_DTL_ID` join | ✅ **VERIFIED** | 100% exact source-native join key |
| **Real Population** | 106,261 18th Lok Sabha projects screened | ✅ **VERIFIED** | Full screening saved in `scored_work_summary.parquet` |
| **Non-Fabrication** | Level 3 physical progress strictly unavailable | ✅ **VERIFIED** | Labeled `UNAVAILABLE_IN_SOURCE`; no synthetic data |
| **Neutral Language** | No claims of fraud, guilt, corruption, or crime | ✅ **VERIFIED** | Purely objective risk, anomalies, and review steps |
| **Screenshot Count** | Exactly 8 high-resolution visual proof images | ✅ **VERIFIED** | Archived in `artifacts/screenshots/` & Desktop |

---

## 2. Official Test Verification Results

Automated test execution output from `.venv\Scripts\python.exe -m pytest tests/ -v`:

```
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0 -- C:\Users\ACER\MPLADS-Risk-Engine\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: C:\Users\ACER\MPLADS-Risk-Engine
plugins: anyio-4.15.0
collecting ... collected 26 items

tests/test_duplicate_blocking.py::test_duplicate_minilm_semantic_path_and_same_context PASSED [  3%]
tests/test_duplicate_blocking.py::test_duplicate_threshold_configurability PASSED [  7%]
tests/test_duplicate_blocking.py::test_different_context_blocked PASSED  [ 11%]
tests/test_duplicate_blocking.py::test_unrelated_descriptions_same_block PASSED [ 15%]
tests/test_duplicate_blocking.py::test_possible_overlap_semantic_similarity PASSED [ 19%]
tests/test_fusion.py::test_fusion_all_four_modules_available PASSED      [ 23%]
tests/test_fusion.py::test_fusion_one_module_missing_renormalization PASSED [ 26%]
tests/test_fusion.py::test_fusion_multiple_modules_missing PASSED        [ 30%]
tests/test_fusion.py::test_fusion_all_modules_missing PASSED             [ 34%]
tests/test_risk_bands_exact PASSED                       [ 38%]
tests/test_evidence_traceability_and_structure PASSED    [ 42%]
tests/test_no_fabrication_level_3_physical_progress PASSED [ 46%]
tests/test_investigation_actions_objective_no_fraud_claims PASSED [ 50%]
tests/test_real_data_style_two_modules_available_renormalization PASSED [ 53%]
tests/test_join_validation.py::test_exact_join_and_orphan_handling PASSED [ 57%]
tests/test_peer_fallback.py::test_step_1_selection_when_cohort_sufficient PASSED [ 61%]
tests/test_peer_fallback.py::test_step_2_fallback_when_year_split_thin PASSED [ 65%]
tests/test_peer_fallback.py::test_step_3_fallback_to_state_year PASSED   [ 69%]
tests/test_peer_fallback.py::test_step_4_fallback_to_state_category PASSED [ 73%]
tests/test_peer_fallback.py::test_step_5_fallback_to_national PASSED     [ 76%]
tests/test_peer_fallback.py::test_insufficient_peers_at_all_levels PASSED [ 80%]
tests/test_scoring.py::test_peer_benchmark_scoring_bounds PASSED         [ 84%]
tests/test_scoring.py::test_peer_benchmark_missing_data_not_zero PASSED  [ 88%]
tests/test_statistical_outlier_zero_dispersion_safety PASSED [ 92%]
tests/test_statistical_outlier_bounds_and_missing PASSED [ 96%]
tests/test_mismatch_engine_peer_duration_and_tiers PASSED [100%]

============================= 26 passed in 30.30s =============================
```

---

## 3. Real Data Source & Exact-Join Validation

All datasets originate from authenticated Government of India MoSPI MPLADS API endpoints for the **18th Lok Sabha**:

| Dataset | Records | Role | Join Key Used | Match Count | Match % |
| :--- | :---: | :--- | :--- | :---: | :---: |
| `works_recommended.json` | 106,261 | Primary baseline population | `WORK_RECOMMENDATION_DTL_ID` | 106,261 | 100.0% |
| `works_completed.json` | 34,259 | Completed works milestone & tenure | `WORK_RECOMMENDATION_DTL_ID` | 34,129 | 99.62% |
| `expenditure_completed_ongoing.json` | 83,907 | Vendor-level disbursed expenditure | `WORK_RECOMMENDATION_DTL_ID` | 83,546 | 99.57% |
| `allocated_limit_mps.json` | 543 | MP allocations & parliamentary limits | MP Name / Identifier | 543 | 100.0% |

*Audit Note on Orphans*: Exactly 130 completed records lacked a matching parent recommendation in `works_recommended.json`. In accordance with locked specifications, these 130 orphans are retained in data audit tables for coverage reporting but excluded from joined risk scoring.

---

## 4. Representative Case Verification

The following real 18th Lok Sabha cases verify mathematical consistency across the Executive Dashboard, Ranked Queue, Work Investigation Dossier, and serialized outputs (`artifacts/demo_outputs/sample_final_work_risk_outputs.json`):

### Case 1: Outlier Recommended Cost (`DTL 303957`)
- **Project**: Construction of Modern Indoor Stadium Badminton Court & Pickleball Court near Amnour Community Centre
- **MP**: Rajiv Pratap Rudy | **Location**: Saran, Bihar | **Stage**: Pending for Sanction
- **Recommended Cost**: ₹9,99,65,000 (₹10.00 Cr) | **Cohort Median**: ₹10,50,612 (₹10.51 Lakh)
- **Peer Benchmarking (30%)**: `100.0` (98.7th percentile, 95.2x peer median; Step 1: District + Category + Year, $n=37$)
- **Statistical Outliers (25%)**: `66.67` (Recommended: 100.0, Sanctioned: 100.0, Ratio: 0.0)
- **Financial Mismatch (30%)**: `UNAVAILABLE (—)` (Lacks execution & disbursement records)
- **Duplicate / Overlap (15%)**: `UNAVAILABLE (—)` (No candidate works within contextual block)
- **Evidence Coverage**: **`55.0%`** ($(0.30 + 0.25) \times 100\%$)
- **Final Risk Score**:
  $$\frac{0.30 \times 100.0 + 0.25 \times 66.67}{0.30 + 0.25} = \frac{46.6675}{0.55} = \mathbf{84.85}$$
- **Risk Band**: **`CRITICAL`** (Consistent across Queue, Dossier, and Parquet summary)

### Case 2: Duplicate / Overlap Candidate (`DTL 133166`)
- **Project**: Construction of Community Bhavan at Navalgund TQ Belavatagi Village Pry No 1/A Near Shivanand Math Continue Work
- **MP**: Pralhad Venkatesh Joshi | **Location**: Dharwad, Karnataka | **Stage**: Physical Inspection
- **Recommended Cost**: ₹4,97,185 | **Cohort Median**: ₹3,99,304 ($n=13$)
- **Duplicate / Overlap (15%)**: `94.0` (`all-MiniLM-L6-v2` Cosine Sim: `0.881`, Agency Match: `100.0%`, Top Match: DTL 254661)
- **Peer Benchmarking (30%)**: `25.38` | **Statistical Outliers (25%)**: `5.15` | **Financial Mismatch (30%)**: `0.0`
- **Evidence Coverage**: **`100.0%`** | **Final Risk Score**: **`23.0`** | **Risk Band**: **`LOW`**

### Case 3: Fully Observed Completed Project (`DTL 133301`)
- **Project**: Construction of Cultural Bhavan at Kundagol TQ, Chickgungal Village
- **MP**: Pralhad Venkatesh Joshi | **Location**: Dharwad, Karnataka | **Stage**: Completed
- **Evidence Coverage**: **`100.0%`** (Has recommendation, completion date, and disbursed expenditure)
- **Duplicate Score**: `95.0` (Top match DTL 206381, Cosine Sim: `0.895`) | **Final Risk Score**: **`17.84`** | **Risk Band**: **`LOW`**

### Case 4: Stalled Execution Tracking (`DTL 133167`)
- **Project**: Community development work in Dharwad, Karnataka
- **Stage**: Pending for Sanction (>365 days delay tracking)
- **Evidence Coverage**: **`85.0%`** | **Final Risk Score**: **`10.36`** | **Risk Band**: **`LOW`**

### Case 5: Normal Low-Risk Baseline (`DTL 133303`)
- **Project**: Standard rural infrastructure project within cohort median
- **Evidence Coverage**: **`100.0%`** | **Final Risk Score**: **`18.11`** | **Risk Band**: **`LOW`**

---

## 5. Frozen Screenshot Artifact Verification

Exactly **8** high-resolution PNG screenshots are captured and archived in:
- `artifacts/screenshots/`
- `C:\Users\ACER\Desktop\MPLADS_Final_Screenshots\`

| Filename | Dimensions | Description |
| :--- | :---: | :--- |
| `01_executive_dashboard.png` | 1440 × 950 | Executive KPIs, 106,261 screened works, risk band breakdown, priority queue cards |
| `02_ranked_risk_queue.png` | 1440 × 950 | Ranked queue with availability-normalized scores, unavailable `—` markers |
| `03_work_investigation_view.png` | 1440 × 950 | DTL 303957 investigation dossier: `CRITICAL (84.8)`, Coverage `55.0%` |
| `04_evidence_module_breakdown.png` | 1440 × 950 | Multi-engine breakdown: Peer (100.0), Stat (66.7), Mismatch (—), Duplicate (—) |
| `04b_investigation_actions.png` | 1440 × 950 | Concrete, non-accusatory field/desk audit action checklists |
| `05_risk_distributions.png` | 1440 × 950 | Portfolio risk distributions, coverage curves, and category breakdowns |
| `06_methodology_provenance.png` | 1440 × 950 | Exact join keys, MoSPI API record counts, and module weighting table |
| `07_duplicate_investigation_view.png` | 1440 × 950 | DTL 133166 dense MiniLM semantic similarity & RapidFuzz agency overlap breakdown |

---

## 6. Forbidden Implementation Audit (Negative Verification)

A codebase audit confirmed zero presence of prohibited methods or terminology:
- **Isolation Forest as primary detector**: ❌ None (Modified Z-score / MAD used)
- **SHAP**: ❌ None
- **GPS / Geolocation fabrication**: ❌ None (Blocked by contextual administrative boundaries)
- **Synthetic physical progress**: ❌ None (Strictly labeled `UNAVAILABLE_IN_SOURCE`)
- **Fabricated project expenditure joins**: ❌ None (Only exact `WORK_RECOMMENDATION_DTL_ID`)
- **Benford's Law**: ❌ None
- **Survival / forecasting completion models**: ❌ None
- **Accusatory / fraud claims**: ❌ None (Strictly neutral terminology: "Risk", "Anomaly", "Review")

---

## 7. Known Limitations & Responsible System Disclaimers

1. **Source Data Coverage Boundary**: Public MoSPI MPLADS API endpoints publish recommendation amounts, administrative sanction stages, completion milestone dates, and vendor disbursement line items. **Physical inspection reports, percentage milestones (e.g. 50% concrete poured), and site photographs are not published in the source system.** The engine honors this by marking Level 3 physical execution as `UNAVAILABLE_IN_SOURCE`.
2. **First-Pass Calibration of Duplicate Thresholds**: The 85% / 70% semantic thresholds for `all-MiniLM-L6-v2` embeddings and RapidFuzz agency scoring are first-pass calibrated screening heuristics. They are configurable in `config/thresholds.yaml` and serve as investigative triage leads, not legally validated duplicate determinations.
3. **Non-Accusatory Investigative Principle**: High risk scores indicate mathematical divergence from cohort norms or missing milestone documentation; they do not imply confirmed financial irregularity or misconduct.

---

## 8. Exact 3–5 Minute Judge Presentation Flow

```
1. Executive Dashboard (1 min)
   • Show top KPIs: 106,261 works, 1,033 priority investigations, average risk 16.5 / 100.
   • Highlight the Evidence Integrity Callout: Explain availability-normalized fusion
     and why missing data must never be treated as zero compliance.

2. Ranked Risk Queue (45 sec)
   • Demonstrate priority sorting and multi-field filters (State, Constituency, Category).
   • Point out unavailable modules rendered cleanly as em-dashes (—), never zero.
   • Show one-click navigation to load a project dossier.

3. Outlier Investigation Dossier — DTL 303957 (1.5 min)
   • Load Rajiv Pratap Rudy's ₹10.00 Cr stadium project in Saran, Bihar.
   • Show that Risk Score is 84.85 (CRITICAL) with 55.0% Evidence Coverage.
   • Open Peer Benchmarking card: show 5-step fallback to Step 1 (District, Category, Year, n=37)
     with project at the 98.7th percentile (95.2x peer median).
   • Open Statistical Outliers card: show robust Modified Z-score sub-scores.
   • Open Financial Mismatch & Duplicate cards: show they are cleanly marked UNAVAILABLE.
   • Review Recommended Investigation Actions: show concrete, non-accusatory field audit steps.

4. Semantic Duplicate Detection — DTL 133166 (45 sec)
   • Load DTL 133166 in Dharwad, Karnataka.
   • Show dense all-MiniLM-L6-v2 semantic cosine similarity (0.881) and 100% agency match
     with pre-existing Community Bhavan project DTL 254661.
   • Explain candidate blocking: avoids quadratic O(N²) explosion by pre-filtering by district/constituency.

5. Provenance & Architecture (30 sec)
   • Open Methodology & Provenance tab: show 100% exact joins on WORK_RECOMMENDATION_DTL_ID.
   • Show 26/26 passing automated tests and sub-second Parquet loading.
```

---

## 9. Reproducibility & Final Run Instructions

To replicate and run the submission package on any standard environment:

```bash
# 1. Clone repository and navigate to root
cd MPLADS-Risk-Engine

# 2. Activate virtual environment
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# 3. Verify requirements
pip install -r requirements.txt
pip install streamlit

# 4. Run full test suite (26/26 passing)
python -m pytest tests/ -v

# 5. Launch official Streamlit Command Center
streamlit run app.py --server.port 8501
```
Open your browser at: `http://localhost:8501`

**FINAL STATUS**: All steps complete. System locked and ready for evaluation.
