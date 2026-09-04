"""UI Styling and Visualization Helpers for the Streamlit Command Center.

Provides:
- Dark professional government-grade CSS stylesheet
- Risk band color mappings and HTML badge renderers
- Currency and number formatting (INR ₹ format)
- Metric card HTML generators
"""

from typing import Optional, Union, Dict, Any

# Semantic risk color palette
RISK_COLORS = {
    "LOW": "#238636",       # Muted green
    "MEDIUM": "#d29922",    # Amber/gold
    "HIGH": "#db6d28",      # Vibrant orange
    "CRITICAL": "#da3633",  # Deep crimson
    "UNAVAILABLE": "#6e7681"# Slate gray
}

RISK_BG_COLORS = {
    "LOW": "rgba(35, 134, 54, 0.15)",
    "MEDIUM": "rgba(210, 153, 34, 0.15)",
    "HIGH": "rgba(219, 109, 40, 0.15)",
    "CRITICAL": "rgba(218, 54, 51, 0.15)",
    "UNAVAILABLE": "rgba(110, 118, 129, 0.15)"
}

CONFIDENCE_COLORS = {
    "LOW": "#8b949e",
    "MEDIUM": "#58a6ff",
    "HIGH": "#3fb950",
    "VERY HIGH": "#a371f7",
    "NONE": "#6e7681"
}


def get_risk_badge_html(risk_band: str, score: Optional[float] = None) -> str:
    """Generates an HTML risk badge pill with semantic color styling."""
    band = (risk_band or "UNAVAILABLE").upper()
    color = RISK_COLORS.get(band, "#6e7681")
    bg = RISK_BG_COLORS.get(band, "rgba(110, 118, 129, 0.15)")
    score_str = f" ({score:.1f})" if score is not None else ""
    return (
        f'<span style="background-color: {bg}; color: {color}; border: 1px solid {color}; '
        f'padding: 3px 10px; border-radius: 12px; font-weight: 600; font-size: 0.85rem; '
        f'letter-spacing: 0.5px; display: inline-block;">'
        f'{band}{score_str}</span>'
    )


def get_confidence_badge_html(conf_label: str) -> str:
    """Generates an HTML confidence tier badge."""
    conf = (conf_label or "NONE").upper()
    color = CONFIDENCE_COLORS.get(conf, "#8b949e")
    return (
        f'<span style="background-color: rgba(110, 118, 129, 0.12); color: {color}; border: 1px solid {color}; '
        f'padding: 2px 8px; border-radius: 4px; font-weight: 600; font-size: 0.75rem; '
        f'text-transform: uppercase; letter-spacing: 0.5px;">'
        f'{conf} CONFIDENCE</span>'
    )


def format_inr(amount: Optional[Union[float, int]]) -> str:
    """Formats a numeric value into INR currency string with Rupee symbol."""
    if amount is None or (isinstance(amount, float) and (amount != amount or amount < 0)):
        return "—"
    try:
        val = float(amount)
        if val >= 10000000:
            return f"₹{val / 10000000:.2f} Cr"
        elif val >= 100000:
            return f"₹{val / 100000:.2f} Lakh"
        else:
            return f"₹{val:,.0f}"
    except (ValueError, TypeError):
        return "—"


def get_metric_card_html(title: str, value: str, subtext: str = "", border_color: str = "#30363d") -> str:
    """Generates a styled KPI metric card container."""
    return f"""
    <div style="background-color: #161b22; border: 1px solid {border_color}; border-radius: 8px; padding: 14px 16px; margin-bottom: 8px;">
        <div style="font-size: 0.8rem; font-weight: 600; text-transform: uppercase; color: #8b949e; letter-spacing: 0.5px; margin-bottom: 4px;">{title}</div>
        <div style="font-size: 1.6rem; font-weight: 700; color: #f0f6fc; line-height: 1.2;">{value}</div>
        {f'<div style="font-size: 0.75rem; color: #8b949e; margin-top: 4px;">{subtext}</div>' if subtext else ''}
    </div>
    """


CUSTOM_CSS = """
<style>
    /* Dark professional command center layout */
    .stApp {
        background-color: #0d1117;
        color: #c9d1d9;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    }
    
    /* Top masthead */
    .masthead-container {
        background: linear-gradient(180deg, #161b22 0%, #0d1117 100%);
        border-bottom: 1px solid #30363d;
        padding: 16px 24px 20px 24px;
        margin-bottom: 20px;
        border-radius: 8px;
    }
    
    /* Card containers */
    .investigation-card {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 18px 20px;
        margin-bottom: 16px;
    }
    
    /* Module cards */
    .module-card {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 16px;
        height: 100%;
    }
    
    /* Tables */
    .dataframe {
        background-color: #161b22 !important;
        color: #c9d1d9 !important;
        border: 1px solid #30363d !important;
        border-radius: 6px !important;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #161b22;
        border-right: 1px solid #30363d;
    }
    
    /* Headers */
    h1, h2, h3, h4 {
        color: #f0f6fc !important;
        font-weight: 600 !important;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        border-bottom: 1px solid #30363d;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: transparent;
        border: 1px solid transparent;
        color: #8b949e;
        border-radius: 6px 6px 0 0;
        padding: 8px 16px;
        font-weight: 500;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #21262d !important;
        color: #58a6ff !important;
        border: 1px solid #30363d !important;
        border-bottom: 2px solid #58a6ff !important;
    }

    /* Buttons */
    .stButton > button {
        background-color: #21262d;
        color: #c9d1d9;
        border: 1px solid #30363d;
        border-radius: 6px;
        font-weight: 500;
        transition: all 0.15s ease-in-out;
    }
    
    .stButton > button:hover {
        background-color: #30363d;
        color: #f0f6fc;
        border-color: #8b949e;
    }

    /* Action item box */
    .action-box {
        background-color: rgba(31, 111, 235, 0.08);
        border-left: 3px solid #1f6feb;
        padding: 10px 14px;
        margin-bottom: 8px;
        border-radius: 0 6px 6px 0;
        font-size: 0.9rem;
        color: #e6edf3;
    }
</style>
"""
