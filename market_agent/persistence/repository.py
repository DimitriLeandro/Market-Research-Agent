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

    def _get_asset_dirs(self, ticker: str, date_obj: date):
        daily_root = self._get_daily_root(date_obj)
        asset_root = daily_root / "tickers" / ticker
        raw_dir = asset_root / "raw"
        final_dir = asset_root / "final"
        
        # Determine directories but do NOT create them here synchronously
        # We will create them in the save methods
        return raw_dir, final_dir

    def _get_sector_dirs(self, sector: str, date_obj: date):
        daily_root = self._get_daily_root(date_obj)
        sanitized_sector = self._sanitize_filename(sector)
        sector_root = daily_root / "sectors" / sanitized_sector
        return sector_root

    # --- Async wrappers for I/O operations ---

    async def asset_exists(self, ticker: str, date_obj: date) -> bool:
        return await asyncio.to_thread(self._asset_exists_sync, ticker, date_obj)

    def _asset_exists_sync(self, ticker: str, date_obj: date) -> bool:
        _, final_dir = self._get_asset_dirs(ticker, date_obj)
        return (final_dir / "report.json").exists()

    async def save_asset_raw(self, ticker: str, step_name: str, content: str, date_obj: date):
        await asyncio.to_thread(self._save_asset_raw_sync, ticker, step_name, content, date_obj)

    def _save_asset_raw_sync(self, ticker: str, step_name: str, content: str, date_obj: date):
        raw_dir, _ = self._get_asset_dirs(ticker, date_obj)
        raw_dir.mkdir(parents=True, exist_ok=True)
        file_path = raw_dir / f"{step_name}.md"
        with file_path.open("w", encoding="utf-8") as f:
            f.write(content)

    async def save_asset_final(self, ticker: str, data: dict, date_obj: date):
        await asyncio.to_thread(self._save_asset_final_sync, ticker, data, date_obj)

    def _save_asset_final_sync(self, ticker: str, data: dict, date_obj: date):
        _, final_dir = self._get_asset_dirs(ticker, date_obj)
        final_dir.mkdir(parents=True, exist_ok=True)
        with (final_dir / "report.json").open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    async def sector_exists(self, sector: str, date_obj: date) -> bool:
        return await asyncio.to_thread(self._sector_exists_sync, sector, date_obj)

    def _sector_exists_sync(self, sector: str, date_obj: date) -> bool:
        sector_dir = self._get_sector_dirs(sector, date_obj)
        return (
            (sector_dir / "bull_thesis.md").exists() and
            (sector_dir / "bear_thesis.md").exists() and
            (sector_dir / "news.md").exists()
        )

    async def save_sector_research(self, sector: str, step_name: str, content: str, date_obj: date):
        await asyncio.to_thread(self._save_sector_research_sync, sector, step_name, content, date_obj)

    def _save_sector_research_sync(self, sector: str, step_name: str, content: str, date_obj: date):
        sector_dir = self._get_sector_dirs(sector, date_obj)
        sector_dir.mkdir(parents=True, exist_ok=True)
        file_path = sector_dir / f"{step_name}.md"
        with file_path.open("w", encoding="utf-8") as f:
            f.write(content)

    async def load_sector_research(self, sector: str, date_obj: date) -> Dict[str, str]:
        return await asyncio.to_thread(self._load_sector_research_sync, sector, date_obj)

    def _load_sector_research_sync(self, sector: str, date_obj: date) -> Dict[str, str]:
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