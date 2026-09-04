"""
Canonical Schema Mapper for MoSPI MPLADS API Data.

Maps the source-native field names from the four Government of India
MPLADS API responses into the locked canonical schema.

Provenance: Direct MoSPI eSAKSHI API (POST /rest/PreLoginDashboardData/getTilesReportData)
NOT Dataful datasets 22567/22566/22565/18533.
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

# =====================================================================
# DATE PARSING
# =====================================================================
SOURCE_DATE_FORMATS = [
    "%d-%b-%Y",                    # 08-Jul-2024 (primary in Rec/Comp/Exp)
    "%b %d, %Y %I:%M:%S %p",      # Jun 4, 2024 12:00:00 AM (tenure dates)
    "%d-%m-%Y",
    "%Y-%m-%d",
]

def parse_date(val: Optional[str]) -> Optional[str]:
    """Parse source date string to canonical ISO format YYYY-MM-DD, or None."""
    if val is None or not isinstance(val, str):
        return None
    cleaned = val.strip()
    if not cleaned or cleaned.upper() == "NA":
        return None
    for fmt in SOURCE_DATE_FORMATS:
        try:
            d = datetime.strptime(cleaned, fmt)
            return d.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None

# =====================================================================
# AMOUNT PARSING
# =====================================================================
def parse_amount(val) -> Optional[float]:
    """Parse source monetary value to float, or None."""
    if val is None:
        return None
    try:
        f = float(val)
        return f
    except (ValueError, TypeError):
        return None

# =====================================================================
# WORK NUMBER EXTRACTION
# =====================================================================
def extract_unique_work_number(activity_name: Optional[str]) -> Optional[str]:
    """
    Deterministic extraction of WS/MP.../YYYY-YYYY/NNNNN from ACTIVITY_NAME.

    The ACTIVITY_NAME in the Recommended and Completed datasets has the form:
      WS/[\\t ]MP<mp_id>/<fiscal_year>/<dtl_id>-<activity_description>
    or:
      NA-<activity_description>  (when unsanctioned / no work number assigned)

    Returns the normalised work number string with whitespace removed, or None.
    """
    if not activity_name or not isinstance(activity_name, str):
        return None
    cleaned = activity_name.replace('\t', '').strip()
    m = re.match(r'^(WS/\s*MP\d+/\d{4}-\d{4}/\d+)', cleaned)
    if m:
        return re.sub(r'\s+', '', m.group(1))
    return None

def extract_work_description_from_activity(activity_name: Optional[str]) -> Optional[str]:
    """
    Extract the work description portion after the ID prefix in ACTIVITY_NAME.

    For 'WS/MP620/2024-2025/133166-Construction of ...' -> 'Construction of ...'
    For 'NA-Construction of ...' -> 'Construction of ...'
    """
    if not activity_name or not isinstance(activity_name, str):
        return None
    cleaned = activity_name.replace('\t', '').strip()
    # Try WS/... pattern first
    m = re.match(r'^WS/\s*MP\d+/\d{4}-\d{4}/\d+-(.+)$', cleaned)
    if m:
        return m.group(1).strip()
    # Try NA- pattern
    m = re.match(r'^NA-(.+)$', cleaned)
    if m:
        return m.group(1).strip()
    return cleaned

# =====================================================================
# IDA PARSING
# =====================================================================
def parse_ida(ida_name: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """
    Parse IDA_NAME like 'DHARWAD(DEPUTY COMMISSIONER DHARWAR_IDA)' into
    (district_name, implementing_authority).
    """
    if not ida_name or not isinstance(ida_name, str):
        return None, None
    m = re.match(r'^([^(]+)\((.+)\)$', ida_name.strip())
    if m:
        district = m.group(1).strip()
        authority = m.group(2).strip()
        # Remove trailing _IDA if present
        if authority.endswith("_IDA"):
            authority = authority[:-4].strip()
        return district, authority
    return ida_name.strip(), None

# =====================================================================
# HOUSE MAPPING
# =====================================================================
HOUSE_MAP = {
    "2": "Lok Sabha",
    "1": "Rajya Sabha",
    "Lok Sabha": "Lok Sabha",
    "Rajya Sabha": "Rajya Sabha",
}

def map_house(val) -> Optional[str]:
    """Map source HOUSE_OF_PARLIAMENT numeric code or HOUSE_NAME to canonical string."""
    if val is None:
        return None
    return HOUSE_MAP.get(str(val).strip(), str(val).strip() if str(val).strip() else None)

# =====================================================================
# CANONICAL RECORD BUILDERS
# =====================================================================

def canonicalize_recommended(rec: Dict[str, Any]) -> Dict[str, Any]:
    """Map a single Works Recommended source record to the canonical schema."""
    district, authority = parse_ida(rec.get("IDA_NAME"))
    unique_wn = extract_unique_work_number(rec.get("ACTIVITY_NAME"))

    return {
        # Identity
        "work_recommendation_dtl_id": rec.get("WORK_RECOMMENDATION_DTL_ID"),
        "unique_work_number": unique_wn,
        "activity_name_raw": rec.get("ACTIVITY_NAME"),

        # Geography & Parliament
        "mp_name": rec.get("MP_NAME"),
        "house": map_house(rec.get("HOUSE_OF_PARLIAMENT")),
        "state": rec.get("STATE_NAME"),
        "constituency": rec.get("CONSTITUENCY"),
        "constituency_id": rec.get("CONSTITUENCY_ID"),
        "district": district,
        "implementing_authority": authority,
        "ida_name_raw": rec.get("IDA_NAME"),

        # Work details
        "category": rec.get("WORK_CATEGORY"),
        "work_description": rec.get("WORK_DESCRIPTION") or extract_work_description_from_activity(rec.get("ACTIVITY_NAME")),
        "work_stage": rec.get("WORK_STAGE"),
        "letter_no": rec.get("LETTER_NO"),

        # Financial
        "amount_recommended": parse_amount(rec.get("RECOMMENDED_AMOUNT")),
        "amount_sanctioned": parse_amount(rec.get("SANCTION_AMOUNT")),

        # Dates
        "recommendation_date": parse_date(rec.get("RECOMMENDATION_DATE")),
        "sanction_date": parse_date(rec.get("SANCTION_DATE")),
        "tenure_start_date": parse_date(rec.get("TENURE_START_DATE")),
        "tenure_end_date": parse_date(rec.get("TENURE_END_DATE")),

        # Metadata
        "tenure": rec.get("TENURE"),
        "flag": rec.get("FLAG"),
        "file_status": rec.get("FILE_STATUS"),
        "attach_id": rec.get("ATTACH_ID"),

        # Source provenance
        "_source": "mospi_api_works_recommended",
    }

def canonicalize_completed(rec: Dict[str, Any]) -> Dict[str, Any]:
    """Map a single Works Completed source record to the canonical schema."""
    district, authority = parse_ida(rec.get("IDA_NAME"))
    unique_wn = extract_unique_work_number(rec.get("ACTIVITY_NAME"))

    return {
        # Identity
        "work_recommendation_dtl_id": rec.get("WORK_RECOMMENDATION_DTL_ID"),
        "work_id": rec.get("WORK_ID"),
        "unique_work_number": unique_wn,
        "activity_name_raw": rec.get("ACTIVITY_NAME"),

        # Geography & Parliament
        "mp_name": rec.get("MP_NAME"),
        "state": rec.get("STATE_NAME"),
        "constituency": rec.get("CONSTITUENCY"),
        "constituency_id": rec.get("CONSTITUENCY_ID"),
        "district": district,
        "implementing_authority": authority,
        "ida_name_raw": rec.get("IDA_NAME"),

        # Work details
        "category": rec.get("WORK_CATEGORY"),
        "work_description": rec.get("WORK_DESCRIPTION") or extract_work_description_from_activity(rec.get("ACTIVITY_NAME")),
        "letter_no": rec.get("LETTER_NO"),

        # Financial
        "amount_completed": parse_amount(rec.get("ACTUAL_AMOUNT")),

        # Dates
        "completion_date": parse_date(rec.get("ACTUAL_END_DATE")),

        # Quality
        "average_rating": rec.get("AVERAGE_RATING"),

        # Source provenance
        "_source": "mospi_api_works_completed",
    }

def canonicalize_expenditure(rec: Dict[str, Any]) -> Dict[str, Any]:
    """Map a single Expenditure source record to the canonical schema."""
    district, authority = parse_ida(rec.get("IDA_NAME"))

    return {
        # Identity
        "work_recommendation_dtl_id": rec.get("WORK_RECOMMENDATION_DTL_ID"),
        "work_id": rec.get("WORK_ID"),

        # Geography & Parliament
        "mp_name": rec.get("MP_NAME"),
        "house": map_house(rec.get("HOUSE_OF_PARLIAMENT")),
        "state": rec.get("STATE_NAME"),
        "constituency": rec.get("CONSTITUENCY"),
        "district": district,
        "implementing_authority": authority,

        # Vendor
        "vendor_name": rec.get("VENDOR_NAME"),
        "vendor_id": rec.get("VENDOR_ID"),
        "implementing_agency": rec.get("IA_NAME"),

        # Financial
        "fund_disbursed_amount": parse_amount(rec.get("FUND_DISBURSED_AMT")),

        # Dates
        "expenditure_date": parse_date(rec.get("EXPENDITURE_DATE")),

        # Work status
        "work_status": rec.get("WORK_STATUS"),
        "letter_no": rec.get("LETTER_NO"),

        # Source provenance
        "_source": "mospi_api_expenditure",
    }

def canonicalize_allocation(rec: Dict[str, Any]) -> Dict[str, Any]:
    """Map a single Allocated Limit source record to the canonical schema."""
    return {
        "mp_name": rec.get("MP_NAME"),
        "house": map_house(rec.get("HOUSE_OF_PARLIAMENT")) or rec.get("HOUSE_NAME"),
        "state": rec.get("STATE_NAME"),
        "constituency": rec.get("CONSTITUENCY"),
        "allocated_amount": parse_amount(rec.get("ALLOCATED_AMT")),
        "tenure": rec.get("TENURE"),
        "tenure_start_date": parse_date(rec.get("TENURE_START_DATE")),
        "tenure_end_date": parse_date(rec.get("TENURE_END_DATE")),
        "_source": "mospi_api_allocated_limit",
    }
