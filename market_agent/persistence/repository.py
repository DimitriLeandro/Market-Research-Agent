import json
import logging
from pathlib import Path
from datetime import date
from typing import Optional, Dict

logger = logging.getLogger(__name__)

class ResearchRepository:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir

    def _get_daily_dir(self, date_obj: date) -> Path:
        path = self.base_dir / date_obj.strftime("%Y_%m_%d")
        path.mkdir(parents=True, exist_ok=True)
        return path

    def exists(self, ticker: str, date_obj: date) -> bool:
        path = self._get_daily_dir(date_obj) / f"{ticker}_data.json"
        return path.exists()

    def save(self, ticker: str, data: dict, report: str, date_obj: date):
        """Atomic-like save: save data first, then report."""
        daily_dir = self._get_daily_dir(date_obj)
        
        json_path = daily_dir / f"{ticker}_data.json"
        md_path = daily_dir / f"{ticker}_report.md"

        try:
            with json_path.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            with md_path.open("w", encoding="utf-8") as f:
                f.write(report)
        except Exception as e:
            logger.error(f"Failed to save data for {ticker}: {e}")
            raise e

    def load_json(self, ticker: str, date_obj: date) -> Optional[Dict]:
        path = self._get_daily_dir(date_obj) / f"{ticker}_data.json"
        if path.exists():
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        return None