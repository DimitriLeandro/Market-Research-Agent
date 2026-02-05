import json
import logging
import re
import asyncio
from pathlib import Path
from datetime import date
from typing import Dict, Any

logger = logging.getLogger(__name__)

class ResearchRepository:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir

    def _sanitize_filename(self, name: str) -> str:
        return re.sub(r'[<>:"/\\|?*]', '_', name)

    def _get_daily_root(self, date_obj: date) -> Path:
        return self.base_dir / date_obj.strftime("%Y_%m_%d")

    def _get_asset_dirs(self, ticker: str, category: str, date_obj: date):
        """
        category: 'stocks' or 'reits'
        Structure: results/date/stocks/ticker/raw|final
        """
        daily_root = self._get_daily_root(date_obj)
        # category corresponds to asset.prompt_subdir (stocks/reits)
        asset_root = daily_root / category / ticker
        
        raw_dir = asset_root / "raw"
        final_dir = asset_root / "final"
        
        return raw_dir, final_dir

    def _get_sector_dirs(self, sector: str, date_obj: date):
        """
        Structure: results/date/sectors/sector/raw|final
        """
        daily_root = self._get_daily_root(date_obj)
        sanitized_sector = self._sanitize_filename(sector)
        sector_root = daily_root / "sectors" / sanitized_sector
        
        raw_dir = sector_root / "raw"
        final_dir = sector_root / "final"
        
        return raw_dir, final_dir

    # --- Asset Methods ---

    async def asset_exists(self, ticker: str, category: str, date_obj: date) -> bool:
        return await asyncio.to_thread(self._asset_exists_sync, ticker, category, date_obj)

    def _asset_exists_sync(self, ticker: str, category: str, date_obj: date) -> bool:
        _, final_dir = self._get_asset_dirs(ticker, category, date_obj)
        return (final_dir / "report.json").exists()

    async def save_asset_raw(self, ticker: str, category: str, step_name: str, content: str, date_obj: date):
        await asyncio.to_thread(self._save_asset_raw_sync, ticker, category, step_name, content, date_obj)

    def _save_asset_raw_sync(self, ticker: str, category: str, step_name: str, content: str, date_obj: date):
        raw_dir, _ = self._get_asset_dirs(ticker, category, date_obj)
        raw_dir.mkdir(parents=True, exist_ok=True)
        file_path = raw_dir / f"{step_name}.md"
        with file_path.open("w", encoding="utf-8") as f:
            f.write(content)

    async def save_asset_final(self, ticker: str, category: str, data: dict, date_obj: date):
        await asyncio.to_thread(self._save_asset_final_sync, ticker, category, data, date_obj)

    def _save_asset_final_sync(self, ticker: str, category: str, data: dict, date_obj: date):
        _, final_dir = self._get_asset_dirs(ticker, category, date_obj)
        final_dir.mkdir(parents=True, exist_ok=True)
        with (final_dir / "report.json").open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    # --- Sector Methods ---

    async def sector_exists(self, sector: str, date_obj: date) -> bool:
        return await asyncio.to_thread(self._sector_exists_sync, sector, date_obj)

    def _sector_exists_sync(self, sector: str, date_obj: date) -> bool:
        _, final_dir = self._get_sector_dirs(sector, date_obj)
        return (final_dir / "report.json").exists()

    async def save_sector_raw(self, sector: str, step_name: str, content: str, date_obj: date):
        await asyncio.to_thread(self._save_sector_raw_sync, sector, step_name, content, date_obj)

    def _save_sector_raw_sync(self, sector: str, step_name: str, content: str, date_obj: date):
        raw_dir, _ = self._get_sector_dirs(sector, date_obj)
        raw_dir.mkdir(parents=True, exist_ok=True)
        file_path = raw_dir / f"{step_name}.md"
        with file_path.open("w", encoding="utf-8") as f:
            f.write(content)

    async def save_sector_final(self, sector: str, data: dict, date_obj: date):
        await asyncio.to_thread(self._save_sector_final_sync, sector, data, date_obj)

    def _save_sector_final_sync(self, sector: str, data: dict, date_obj: date):
        _, final_dir = self._get_sector_dirs(sector, date_obj)
        final_dir.mkdir(parents=True, exist_ok=True)
        with (final_dir / "report.json").open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    async def load_sector_research(self, sector: str, date_obj: date) -> Dict[str, str]:
        return await asyncio.to_thread(self._load_sector_research_sync, sector, date_obj)

    def _load_sector_research_sync(self, sector: str, date_obj: date) -> Dict[str, str]:
        raw_dir, _ = self._get_sector_dirs(sector, date_obj)
        data = {}
        for step in ['bull_thesis', 'bear_thesis', 'news']:
            path = raw_dir / f"{step}.md"
            if path.exists():
                with path.open("r", encoding="utf-8") as f:
                    data[step] = f.read()
            else:
                data[step] = "No data found."
        return data