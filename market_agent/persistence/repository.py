import json
import logging
from pathlib import Path
from datetime import date
from typing import Optional, Dict

logger = logging.getLogger(__name__)

class ResearchRepository:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir

    def _get_asset_dirs(self, ticker: str, date_obj: date):
        daily_root = self.base_dir / date_obj.strftime("%Y_%m_%d")
        asset_root = daily_root / ticker
        
        raw_dir = asset_root / "raw"
        final_dir = asset_root / "final"
        
        raw_dir.mkdir(parents=True, exist_ok=True)
        final_dir.mkdir(parents=True, exist_ok=True)
        
        return raw_dir, final_dir

    def exists(self, ticker: str, date_obj: date) -> bool:
        # Check if the FINAL report exists in the canonical location
        daily_root = self.base_dir / date_obj.strftime("%Y_%m_%d")
        final_report = daily_root / ticker / "final" / "report.json"
        return final_report.exists()

    def save_raw(self, ticker: str, step_name: str, content: str, date_obj: date):
        raw_dir, _ = self._get_asset_dirs(ticker, date_obj)
        file_path = raw_dir / f"{step_name}.md"
        with file_path.open("w", encoding="utf-8") as f:
            f.write(content)

    def save_final(self, ticker: str, data: dict, date_obj: date):
        # NOTE: signature is (ticker, data, date_obj) - 3 args
        _, final_dir = self._get_asset_dirs(ticker, date_obj)
        
        # Save JSON - Canonical Path
        with (final_dir / "report.json").open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)