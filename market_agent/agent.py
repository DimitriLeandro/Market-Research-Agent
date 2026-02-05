import asyncio
import logging
import subprocess
import time
from datetime import date
from typing import List, Set, Dict, Any

from .config.settings import Config
from .assets.base import Asset
from .assets.equity import EquityAsset
from .assets.reit import REITAsset
from .assets.sector import SectorAsset
from .research.provider import GeminiProvider
from .research.enrichment import YFinanceEnricher
from .persistence.repository import ResearchRepository

logger = logging.getLogger(__name__)

class MarketAgent:
    def __init__(self, test_mode: bool = False):
        self.test_mode = test_mode
        self.api_key = Config.load_api_key()
        
        self.global_semaphore = asyncio.Semaphore(Config.MAX_CONCURRENT_REQUESTS)
        self.provider = GeminiProvider(self.api_key, self.global_semaphore)
        
        self.enricher = YFinanceEnricher()
        self.repository = ResearchRepository(Config.RESULTS_DIR)
        
        self.assets = self._load_assets()
        self.sectors = self._identify_sectors()

        mode_label = "TEST MODE" if self.test_mode else "PRODUCTION MODE"
        logger.info(f"MarketAgent initialized in {mode_label}. Max Parallel Requests: {Config.MAX_CONCURRENT_REQUESTS}")

    def _load_assets(self) -> List[Asset]:
        raw = Config.load_portfolio(test_mode=self.test_mode)
        assets = []
        for item in raw:
            asset_data = item.copy()
            asset_type_str = asset_data.pop('type')
            asset_data['asset_type'] = asset_type_str

            if asset_type_str == 'equity':
                assets.append(EquityAsset(**asset_data))
            elif asset_type_str == 'reit':
                assets.append(REITAsset(**asset_data))
        return assets

    def _identify_sectors(self) -> List[SectorAsset]:
        unique_sector_names = set(asset.sector for asset in self.assets)
        sector_assets = []
        for name in unique_sector_names:
            sector_assets.append(
                SectorAsset(
                    ticker=name,
                    name=name,
                    asset_type="sector",
                    sector=name
                )
            )
        return sector_assets

    async def _process_sector(self, sector_asset: SectorAsset, today: date) -> Dict[str, str]:
        sector_name = sector_asset.ticker
        logger.info(f"[{sector_name}] Starting Sector Pipeline...")
        try:
            if await self.repository.sector_exists(sector_name, today):
                logger.info(f"[{sector_name}] Loaded from cache.")
                # We need to return a dict to support asset tasks, but loading generic research is tricky
                # if we only have the synthesis. For now, we rely on raw files if they exist or 
                # rebuild the cache map from raw files.
                return await self.repository.load_sector_research(sector_name, today)

            t_bull = self.provider.research_sector_bull(sector_name)
            t_bear = self.provider.research_sector_bear(sector_name)
            t_news = self.provider.research_sector_news(sector_name)

            bull, bear, news = await asyncio.gather(t_bull, t_bear, t_news)

            await self.repository.save_sector_raw(sector_name, "bull_thesis", bull, today)
            await self.repository.save_sector_raw(sector_name, "bear_thesis", bear, today)
            await self.repository.save_sector_raw(sector_name, "news", news, today)
            
            logger.info(f"[{sector_name}] Synthesizing markdown report...")
            synthesis = await self.provider.synthesize_analysis(
                "sectors/synthesis.j2",
                {
                    "sector": sector_name,
                    "bull_thesis": bull,
                    "bear_thesis": bear,
                    "news": news
                }
            )
            
            # Save Markdown Synthesis to RAW (intermediate step)
            await self.repository.save_sector_raw(sector_name, "synthesis", synthesis, today)
            
            logger.info(f"[{sector_name}] Completed.")
            
            # Return context for assets
            return {
                "bull_thesis": bull,
                "bear_thesis": bear,
                "news": news,
                "synthesis": synthesis
            }

        except Exception as e:
            logger.error(f"[{sector_name}] Failed: {e}", exc_info=True)
            return {"synthesis": "Error during sector processing"}

    async def _process_asset(self, asset: Asset, sector_task: asyncio.Task, today: date):
        category = asset.prompt_subdir
        logger.info(f"[{asset.ticker}] Starting Asset Pipeline ({category})...")
        
        try:
            # We skip the check for final report.json existence because we aren't generating it yet.
            # Only checking if synthesis already exists could be an optimization, but let's run fully for now.

            tasks_map = {
                "bull_thesis": self.provider.research_asset_bull(asset),
                "bear_thesis": self.provider.research_asset_bear(asset),
                "financials": self.provider.research_asset_financials(asset),
                "news": self.provider.research_asset_news(asset),
                "filings": self.provider.research_asset_filings(asset)
            }

            if isinstance(asset, EquityAsset):
                tasks_map["earnings"] = self.provider.research_asset_earnings(asset)
            elif isinstance(asset, REITAsset):
                tasks_map["management"] = self.provider.research_asset_management(asset)

            keys = list(tasks_map.keys())
            coroutines = list(tasks_map.values())
            
            results_list = await asyncio.gather(*coroutines)
            results = dict(zip(keys, results_list))

            save_coroutines = []
            for step_name, content in results.items():
                save_coroutines.append(
                    self.repository.save_asset_raw(asset.ticker, category, step_name, content, today)
                )

            await asyncio.gather(*save_coroutines)

            logger.info(f"[{asset.ticker}] Waiting for sector data ({asset.sector})...")
            sector_data_map = await sector_task
            
            # We use the sector synthesis as the context to feed into the asset synthesis
            sector_context = sector_data_map.get("synthesis", "Dados do setor indisponíveis.")

            logger.info(f"[{asset.ticker}] Synthesizing markdown report...")
            
            context = {
                "ticker": asset.ticker,
                "sector": asset.sector,
                "sector_data": sector_context,
                **results # Unpack all research results (bull, bear, etc) into context
            }
            
            synthesis = await self.provider.synthesize_analysis(
                f"{category}/synthesis.j2",
                context
            )

            # Save Markdown Synthesis to RAW
            await self.repository.save_asset_raw(asset.ticker, category, "synthesis", synthesis, today)

            logger.info(f"[{asset.ticker}] Synthesis saved to raw/synthesis.md. (JSON generation pending Phase 3).")

        except Exception as e:
            logger.error(f"[{asset.ticker}] Failed: {e}", exc_info=True)

    def _git_auto_commit(self):
        today_str = date.today().strftime("%Y-%m-%d")
        mode_str = "TEST" if self.test_mode else "PROD"
        commit_msg = f"docs: adding {today_str} results ({mode_str} auto commit)"
        
        max_retries = 5
        attempts = 0
        
        while attempts <= max_retries:
            try:
                subprocess.run(["git", "add", "results/"], check=True, capture_output=True, text=True)
                try:
                    subprocess.run(["git", "commit", "-m", commit_msg], check=True, capture_output=True, text=True)
                except subprocess.CalledProcessError as e:
                    if "nothing to commit" in e.stdout.lower():
                        logger.info("Git: Nothing to commit.")
                        return
                    raise e 

                subprocess.run(["git", "push"], check=True, capture_output=True, text=True)
                logger.info(f"Git auto-commit successful: {commit_msg}")
                return

            except subprocess.CalledProcessError as e:
                sleep_time = 2 ** attempts
                if attempts < max_retries:
                    logger.warning(f"Git auto-commit attempt {attempts + 1} failed. Retrying in {sleep_time}s...")
                    time.sleep(sleep_time)
                    attempts += 1
                else:
                    logger.error(f"Git auto-commit failed: {e}")
                    return

    async def run_cycle(self):
        today = date.today()
        logger.info(f"Cycle Date: {today}")

        sector_tasks_map: Dict[str, asyncio.Task] = {}
        
        for sector_asset in self.sectors:
            task = asyncio.create_task(self._process_sector(sector_asset, today))
            sector_tasks_map[sector_asset.ticker] = task

        asset_tasks = []
        for asset in self.assets:
            if asset.sector not in sector_tasks_map:
                logger.error(f"Asset {asset.ticker} has unknown sector {asset.sector}. Skipping.")
                continue
            
            sec_task = sector_tasks_map[asset.sector]
            task = asyncio.create_task(self._process_asset(asset, sec_task, today))
            asset_tasks.append(task)
        
        all_tasks = list(sector_tasks_map.values()) + asset_tasks
        if all_tasks:
            logger.info(f"Scheduled {len(sector_tasks_map)} sectors and {len(asset_tasks)} assets. Running...")
            await asyncio.gather(*all_tasks)
        
        logger.info("All research tasks finished.")
        self._git_auto_commit()