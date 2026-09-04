# MPLADS Risk Intelligence & Investigation Engine

> **SIH26102 — Authoritative Government Screening & Multi-Engine Evidence Fusion**  
> Backed by 106,261 authentic Government of India Ministry of Statistics and Programme Implementation (MoSPI) **18th Lok Sabha** MPLADS records.

---

## 1. System Overview

The **MPLADS Risk Intelligence & Investigation Engine** is an audit and risk-screening platform built for field inspection officers, desk auditors, and ministry analysts. It screens Member of Parliament Local Area Development Scheme (MPLADS) projects across India using a multi-engine statistical, financial, and semantic evidence fusion pipeline.

### Core Safeguards & Design Principles
- **Investigative, Not Punitive**: The system detects anomalies, milestone deviations, and duplicate leads. It **never** claims confirmed fraud, guilt, criminality, or corruption.
- **Availability-Normalized Fusion**: Missing or unavailable evidence modules are strictly **excluded from the denominator**, ensuring that unobserved execution milestones do not dilute risk scores or register as false compliance.
- **Strict Non-Fabrication**: Level 3 physical progress percentages do not exist in public datasets and are strictly documented as `UNAVAILABLE_IN_SOURCE`. No synthetic data, GPS fabrication, or fuzzy work-ID joins are used.

---

## 2. Source Data & Provenance

All intelligence is generated from authentic Government of India MoSPI MPLADS API responses for the **18th Lok Sabha**:

| Dataset File | Records | Role | Authoritative Join Key | Exact Match Rate |
| :--- | :---: | :--- | :--- | :---: |
| `works_recommended.json` | 106,261 | Base Recommended Works Population | `WORK_RECOMMENDATION_DTL_ID` | 100.0% |
| `works_completed.json` | 34,259 | Completed Works & Completion Dates | `WORK_RECOMMENDATION_DTL_ID` | 99.62% (34,129 joined) |
| `expenditure_completed_ongoing.json` | 83,907 | Vendor-level Disbursed Expenditure | `WORK_RECOMMENDATION_DTL_ID` | 99.57% (83,546 joined) |
| `allocated_limit_mps.json` | 543 | MP Financial Allocations | MP Identifier / Name | Authoritative Context |

*Note: 130 orphan completed records lacking a parent recommendation are retained for audit and coverage reporting but excluded from joined scoring.*

---

## 3. The Four Locked Core Analytical Engines

The engine combines four specialized, independent analytical modules:

```
+-----------------------------------------------------------------------------+
|                          RAW 18th LOK SABHA DATA                            |
|             (106,261 Recommended • 34,259 Completed • 83,907 Exp)          |
+-----------------------------------------------------------------------------+
                                      │
                                      ▼
+-----------------------------------------------------------------------------+
|             EXACT CANONICAL JOIN (WORK_RECOMMENDATION_DTL_ID)               |
+-----------------------------------------------------------------------------+
       │                             │                     │           │
       ▼                             ▼                     ▼           ▼
┌───────────────┐           ┌─────────────────┐    ┌─────────────┐ ┌───────────┐
|  1. PEER      |           | 2. STATISTICAL  |    | 3. MISMATCH | | 4. DUP    |
|  BENCHMARKING |           |    OUTLIERS     |    |    ENGINE   | |  OVERLAP  |
|  (Weight 30%) |           |  (Weight 25%)   |    | (Weight 30%)| |(Weight15%)|
└───────┬───────┘           └────────┬────────┘    └──────┬──────┘ └─────┬─────┘
        │                            │                    │              │
        └───────────────────────┬────┴────────────────────┴──────────────┘
                                │
                                ▼
        +-------------------------------------------------------------+
        |             AVAILABILITY-NORMALIZED FUSION                  |
        |      Risk Score = Σ(w_m · S_m) / Σ(w_m)  [Clamped 0-100]    |
        |      Evidence Coverage = Σ(w_m) × 100%                      |
        +-------------------------------------------------------------+
                                │
                                ▼
        +-------------------------------------------------------------+
        |               INVESTIGATION COMMAND CENTER                  |
        |  (Ranked Queue • Project Dossier • Concrete Next Steps)     |
        +-------------------------------------------------------------+
```

### 1. Peer Benchmarking (30% Weight)
- Evaluates project recommended cost against peer cohorts using an exact **5-step locked hierarchy**:
  1. District + Category + Year
  2. District + Category
  3. State + Category + Year
  4. State + Category
  5. National + Category
- Minimum cohort target: $N \ge 10$ works. Employs robust median, IQR, empirical percentile rank, and deviation ratios.

### 2. Statistical Outliers (25% Weight)
- Evaluates numeric distributions using robust **Modified Z-Scores** ($0.6745 \cdot |x - \text{median}| / \text{MAD}$).
- Features evaluated: recommended amount, sanctioned amount, sanction-to-recommended ratio, sanction delay days, completed cost ratio, disbursed-to-sanction ratio.
- **Zero-dispersion safety**: features with zero MAD (e.g., identical sanction ratios) are treated as neutral, preventing false-positive division-by-zero spikes.

### 3. Financial–Execution Mismatch (30% Weight)
- 3-tier evidence confidence hierarchy:
  - **Level 1 (Proxy)**: Prolonged pending sanction ($>180$ days) — `LOW` Confidence
  - **Level 1 (Observed Financial)**: Cost overrun, disbursement exceeds sanction — `MEDIUM` Confidence
  - **Level 2 (Time-based)**: Peer duration overrun ($>2.0\times$ peer median), stalled execution with zero disbursement ($>365$ days), timeline inversion — `HIGH` Confidence
  - **Level 3 (Physical Progress)**: Strictly `UNAVAILABLE_IN_SOURCE` — `VERY HIGH` Confidence Tier
- If execution records do not exist, the module strictly returns `available = False` and `score = None`.

### 4. Duplicate / Overlap Detection (15% Weight)
- **Contextual Candidate Blocking**: Blocks works by `(State, Constituency/District, Category)` before embedding inference to bound quadratic complexity.
- **Semantic Text Embeddings**: Computes cosine similarity on normalized work descriptions using `sentence-transformers/all-MiniLM-L6-v2`.
- **Implementing Agency Similarity**: Evaluates agency text similarity using `RapidFuzz`.
- Tri-state classification: `Likely duplicate` ($\ge 85\%$), `Possible overlap` ($\ge 70\%$), `Unrelated`.

---

## 4. Availability-Normalized Scoring & Risk Bands

Risk scores are computed exclusively from modules with valid evidence:

$$\text{Final Risk Score} = \min\left(100.0, \max\left(0.0, \frac{\sum_{m \in \text{Available}} w_m \cdot S_m}{\sum_{m \in \text{Available}} w_m}\right)\right)$$

$$\text{Evidence Coverage} = \left(\sum_{m \in \text{Available}} w_m\right) \times 100\%$$

### Risk Bands
- **0 – 29**: `LOW`
- **30 – 59**: `MEDIUM`
- **60 – 79**: `HIGH`
- **80 – 100**: `CRITICAL`

---

## 5. Quickstart & Installation

### Requirements
- Python 3.10 or higher (tested on Python 3.11.9)
- Windows, Linux, or macOS

### 1. Setup Virtual Environment
```bash
# Clone the repository
git clone https://github.com/your-org/MPLADS-Risk-Engine.git
cd MPLADS-Risk-Engine

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
pip install streamlit
```

### 3. Run Automated Tests
```bash
python -m pytest tests/ -v
```
*Expected: 26 passed in ~30 seconds.*

### 4. Launch Streamlit Command Center
```bash
streamlit run app.py --server.port 8501
```
Open your browser and navigate to:
```
http://localhost:8501
```

---

## 6. Judge-Facing Demonstration Flow

To demonstrate the platform to evaluators, follow this recommended 5-step workflow:

1. **Executive Dashboard (`Tab 1`)**:
   - Inspect portfolio KPIs across the 106,261 active 18th Lok Sabha projects.
   - Review the risk band breakdown: 69 Critical, 964 High, 13,188 Medium, 92,039 Low works.
   - Note the **Evidence Integrity Callout** explaining why Risk Score $\ne$ Evidence Coverage.
2. **Ranked Risk Queue (`Tab 2`)**:
   - Filter by State (e.g., Bihar or Karnataka) or sort by Risk Score descending.
   - Observe that unavailable modules strictly display as `—` (never 0).
   - Select a high-priority work (e.g., `DTL 303957` or `DTL 133166`) and click **Open in Work Investigation View**.
3. **Project Dossier & Multi-Engine Breakdown (`Tab 3`)**:
   - Review the full project description, MP, location, stage, and financial milestones.
   - Inspect the **Peer Benchmarking** card showing the cohort fallback level (Step 1 to 5), peer median, and percentile rank.
   - Inspect the **Statistical Outliers** card showing robust Modified Z-scores and zero-dispersion safety.
   - Inspect the **Financial Mismatch** card showing confidence tier badges and the explicit `UNAVAILABLE_IN_SOURCE` physical progress marker.
   - Inspect the **Duplicate / Overlap** card showing `all-MiniLM-L6-v2` semantic cosine similarity and candidate pairings.
4. **Concrete Investigation Actions (`Tab 3`)**:
   - Review concrete, objective desk and field checks generated for auditors without claims of fraud or guilt.
5. **Portfolio Risk Distributions & Methodology (`Tabs 4 & 5`)**:
   - Inspect geographic risk patterns and authoritative GoI MoSPI dataset provenance.

---

## 7. Project Structure

```
MPLADS-Risk-Engine/
├── app.py                     # Streamlit Command Center Application
├── requirements.txt           # Python dependency specifications
├── README.md                  # Project documentation & run guide
├── config/                    # Configurable thresholds and scoring parameters
├── docs/                      # Architectural specifications & locked build specs
├── data/
│   ├── raw/api_18th/          # Authentic MoSPI 18th Lok Sabha API datasets
│   └── processed/             # Canonical joined master & pre-scored summaries
├── src/
│   ├── validation.py          # Data validation & schema checks
│   ├── canonical.py           # Canonical schema transformation
│   ├── joins.py               # Exact DTL_ID joins & orphan handling
│   ├── peer_benchmark.py      # Engine 1: 5-step peer cohort benchmarking (30%)
│   ├── statistical_outliers.py# Engine 2: Robust Modified Z-scores & MAD (25%)
│   ├── mismatch.py            # Engine 3: Multi-tier financial mismatch (30%)
│   ├── duplicate_overlap.py   # Engine 4: MiniLM embeddings + RapidFuzz (15%)
│   ├── coverage.py            # Evidence coverage calculation
│   ├── fusion.py              # Availability-normalized evidence fusion
│   ├── evidence.py            # Structured evidence objects
│   ├── investigation.py       # Objective next-step investigation actions
│   └── ui_helpers.py          # Dark professional CSS, badges & INR formatters
├── tests/
│   ├── test_duplicate_blocking.py # MiniLM semantic similarity tests
│   ├── test_fusion.py             # Availability normalization & schema tests
│   ├── test_join_validation.py    # Exact join & orphan handling tests
│   ├── test_peer_fallback.py      # 5-step cohort hierarchy tests
│   └── test_scoring.py            # Outlier & mismatch heuristics tests
└── artifacts/
    ├── demo_outputs/          # Scored WorkRisk sample outputs & profiling reports
    └── screenshots/           # High-resolution screenshots of all 8 UI screens
```

---

## 8. License & Provenance

Data sourced directly from the official **Government of India MoSPI MPLADS Portal** (`https://mplads.mospi.gov.in`). Implemented for the Smart India Hackathon (SIH26102).
