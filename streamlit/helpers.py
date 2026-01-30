import json
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# --- PATH FIX: USE ABSOLUTE PATHS BASED ON FILE LOCATION ---
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
RESULTS_DIR = PROJECT_ROOT / "results"

def format_date_uk(date_str: str) -> str:
    """
    Converts YYYY_MM_DD or YYYY-MM-DD to DD/MM/YYYY.
    Returns original string if parsing fails.
    """
    try:
        # Try parsing standard folder format YYYY_MM_DD
        dt = datetime.strptime(date_str, "%Y_%m_%d")
        return dt.strftime("%d/%m/%Y")
    except ValueError:
        try:
            # Try parsing ISO format YYYY-MM-DD
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            return dt.strftime("%d/%m/%Y")
        except ValueError:
            return date_str

def escape_markdown_dollars(text: str) -> str:
    """
    Escapes dollar signs to prevent Streamlit from interpreting them as LaTeX.
    $100 -> \$100
    """
    if not text:
        return ""
    # FIX: Use raw string r"\$" to avoid SyntaxWarning
    return text.replace("$", r"\$")

def get_available_dates() -> List[str]:
    """Returns a sorted list of date folders (YYYY_MM_DD) present in results."""
    if not RESULTS_DIR.exists():
        return []
    
    # regex for YYYY_MM_DD
    date_pattern = re.compile(r"^\d{4}_\d{2}_\d{2}$")
    
    dirs = [d.name for d in RESULTS_DIR.iterdir() if d.is_dir() and date_pattern.match(d.name)]
    return sorted(dirs, reverse=True)

def load_report_data(date_folder_name: str) -> Dict[str, Any]:
    """
    Loads all JSON data for a specific date folder.
    Traverses: Results/DATE/TICKER/final/report.json
    Returns a dict with 'equity' and 'fii' lists.
    """
    target_dir = RESULTS_DIR / date_folder_name
    if not target_dir.exists():
        return {"equity": [], "fii": []}

    data_store = {"equity": [], "fii": []}

    # Iterate over all directories (Tickers) inside the date folder
    for ticker_dir in target_dir.iterdir():
        if not ticker_dir.is_dir():
            continue
            
        json_path = ticker_dir / "final" / "report.json"
        
        if json_path.exists():
            try:
                with json_path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                
                ticker = data.get("ticker", "UNKNOWN")
                
                # Identify type based on ticker suffix
                if "11" in ticker:
                    asset_type = "fii"
                else:
                    asset_type = "equity"
                
                # Pre-format date for UI consistency
                if "analysis_date" in data:
                    data["analysis_date"] = format_date_uk(data["analysis_date"])
                
                data_store[asset_type].append(data)

            except Exception:
                # Silently skip malformed files in UI
                continue

    # Sort by ticker
    data_store["equity"].sort(key=lambda x: x["ticker"])
    data_store["fii"].sort(key=lambda x: x["ticker"])

    return data_store

def get_sentiment_color(score: float) -> str:
    if score >= 0.3: return "green"
    if score <= -0.3: return "red"
    return "gray"

def get_sentiment_emoji(score: float) -> str:
    if score >= 0.5: return "🚀"
    if score >= 0.1: return "📈"
    if score <= -0.5: return "💀"
    if score <= -0.1: return "📉"
    return "⚖️"