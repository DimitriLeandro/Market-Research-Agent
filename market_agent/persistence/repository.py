import json
import logging
import re
from pathlib import Path
from datetime import date
from typing import Dict, Any

logger = logging.getLogger(__name__)

class ResearchRepository:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir

    def _sanitize_filename(self, name: str) -> str:
        """Sanitize strings (like 'Utilities/Energy') for filesystem usage."""
        return re.sub(r'[<>:"/\\|?*]', '_', name)

    def _get_daily_root(self, date_obj: date) -> Path:
        return self.base_dir / date_obj.strftime("%Y_%m_%d")

    def _get_asset_dirs(self, ticker: str, date_obj: date):
        daily_root = self._get_daily_root(date_obj)
        asset_root = daily_root / "tickers" / ticker
        
        raw_dir = asset_root / "raw"
        final_dir = asset_root / "final"
        
        raw_dir.mkdir(parents=True, exist_ok=True)
        final_dir.mkdir(parents=True, exist_ok=True)
        
        return raw_dir, final_dir

    def _get_sector_dirs(self, sector: str, date_obj: date):
        daily_root = self._get_daily_root(date_obj)
        sanitized_sector = self._sanitize_filename(sector)
        sector_root = daily_root / "sectors" / sanitized_sector
        
        sector_root.mkdir(parents=True, exist_ok=True)
        return sector_root

    # --- Asset Methods ---

    def asset_exists(self, ticker: str, date_obj: date) -> bool:
        _, final_dir = self._get_asset_dirs(ticker, date_obj)
        return (final_dir / "report.json").exists()

    def save_asset_raw(self, ticker: str, step_name: str, content: str, date_obj: date):
        raw_dir, _ = self._get_asset_dirs(ticker, date_obj)
        file_path = raw_dir / f"{step_name}.md"
        with file_path.open("w", encoding="utf-8") as f:
            f.write(content)

    def save_asset_final(self, ticker: str, data: dict, date_obj: date):
        _, final_dir = self._get_asset_dirs(ticker, date_obj)
        with (final_dir / "report.json").open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    # --- Sector Methods ---

    def sector_exists(self, sector: str, date_obj: date) -> bool:
        sector_dir = self._get_sector_dirs(sector, date_obj)
        # Check if all 3 required files exist
        return (
            (sector_dir / "bull_thesis.md").exists() and
            (sector_dir / "bear_thesis.md").exists() and
            (sector_dir / "news.md").exists()
        )

    def save_sector_research(self, sector: str, step_name: str, content: str, date_obj: date):
        """
        step_name examples: 'bull_thesis', 'bear_thesis', 'news'
        """
        sector_dir = self._get_sector_dirs(sector, date_obj)
        file_path = sector_dir / f"{step_name}.md"
        with file_path.open("w", encoding="utf-8") as f:
            f.write(content)

    def load_sector_research(self, sector: str, date_obj: date) -> Dict[str, str]:
        sector_dir = self._get_sector_dirs(sector, date_obj)
        data = {}
        for step in ['bull_thesis', 'bear_thesis', 'news']:
            path = sector_dir / f"{step}.md"
            if path.exists():
                with path.open("r", encoding="utf-8") as f:
                    data[step] = f.read()
            else:
                data[step] = "No data found."
        return data