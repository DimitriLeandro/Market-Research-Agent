import json
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# Path Definitions
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
RESULTS_DIR = PROJECT_ROOT / "results"
MAIN_SCRIPT_PATH = PROJECT_ROOT / "market_agent" / "main.py"

def format_date_uk(date_str: str) -> str:
    """
    Converts YYYY_MM_DD or YYYY-MM-DD to DD/MM/YYYY.
    Returns original string if parsing fails.
    """
    if not date_str:
        return "-"
    try:
        dt = datetime.strptime(date_str, "%Y_%m_%d")
        return dt.strftime("%d/%m/%Y")
    except ValueError:
        try:
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
    return text.replace("$", r"\$")

def get_available_dates() -> List[str]:
    """Returns a sorted list of date folders (YYYY_MM_DD) present in results."""
    if not RESULTS_DIR.exists():
        return []
    
    date_pattern = re.compile(r"^\d{4}_\d{2}_\d{2}$")
    dirs = [d.name for d in RESULTS_DIR.iterdir() if d.is_dir() and date_pattern.match(d.name)]
    return sorted(dirs, reverse=True)

def get_dir_for_date(date_str: str) -> Path:
    """Converts display date back to directory path object."""
    return RESULTS_DIR / date_str

def load_reports_by_category(date_dir: Path, category: str) -> List[Dict[str, Any]]:
    """
    Loads all JSON reports for a specific category (stocks, reits, sectors).
    Structure: results/DATE/CATEGORY/ASSET/final/report.json
    Returns a sorted list of dictionaries.
    """
    category_path = date_dir / category
    if not category_path.exists():
        return []

    data_list = []
    
    # Iterate over assets inside the category folder
    for asset_dir in category_path.iterdir():
        if not asset_dir.is_dir():
            continue
            
        report_path = asset_dir / "final" / "report.json"
        
        if report_path.exists():
            try:
                with report_path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                    
                    # Normalize date for UI
                    if "analysis_date" in data:
                        data["analysis_date"] = format_date_uk(data["analysis_date"])
                    
                    data_list.append(data)
            except Exception as e:
                print(f"Error loading {report_path}: {e}")

    # Sort by Ticker or Sector name
    data_list.sort(key=lambda x: x.get("ticker", x.get("sector", "ZZZ")))
    return data_list

def get_sentiment_emoji(sentiment_str: str, score: float = 0.0) -> str:
    """Returns an emoji based on sentiment string or score."""
    s = str(sentiment_str).lower()
    if "bullish" in s: return "🚀"
    if "bearish" in s: return "🐻"
    if "cautious" in s: return "⚠️"
    if "neutral" in s: return "⚖️"
    
    # Fallback based on score
    if score >= 0.1: return "📈"
    if score <= -0.1: return "📉"
    return "😐"