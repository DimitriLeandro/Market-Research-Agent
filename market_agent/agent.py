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
                return await self.repository.load_sector_research(sector_name, today)

            t_bull = self.provider.research_sector_bull(sector_name)
            t_bear = self.provider.research_sector_bear(sector_name)
            t_news = self.provider.research_sector_news(sector_name)

            bull, bear, news = await asyncio.gather(t_bull, t_bear, t_news)

            await self.repository.save_sector_raw(sector_name, "bull_thesis", bull, today)
            await self.repository.save_sector_raw(sector_name, "bear_thesis", bear, today)
            await self.repository.save_sector_raw(sector_name, "news", news, today)
            
            logger.info(f"[{sector_name}] Synthesizing report...")
            synthesis_result = await self.provider.synthesize_sector_report(sector_name, bull, bear, news)
            synthesis_result.analysis_date = today.isoformat()
            
            await self.repository.save_sector_final(
                sector_name, 
                synthesis_result.model_dump(mode='json'), 
                today
            )
            
            logger.info(f"[{sector_name}] Completed.")
            
            return {
                "bull_thesis": bull,
                "bear_thesis": bear,
                "news": news
            }

        except Exception as e:
            logger.error(f"[{sector_name}] Failed: {e}", exc_info=True)
            return {"bull_thesis": "Error", "bear_thesis": "Error", "news": "Error"}

    async def _process_asset(self, asset: Asset, sector_task: asyncio.Task, today: date):
        category = asset.prompt_subdir
        logger.info(f"[{asset.ticker}] Starting Asset Pipeline ({category})...")
        
        try:
            if await self.repository.asset_exists(asset.ticker, category, today):
                logger.info(f"[{asset.ticker}] Loaded from cache.")
                await sector_task 
                return

            t_bull = self.provider.research_asset_bull(asset)
            t_bear = self.provider.research_asset_bear(asset)
            t_fin = self.provider.research_asset_financials(asset)
            t_news = self.provider.research_asset_news(asset)

            bull_res, bear_res, fin_res, news_res = await asyncio.gather(
                t_bull, t_bear, t_fin, t_news
            )

            await asyncio.gather(
                self.repository.save_asset_raw(asset.ticker, category, "bull_thesis", bull_res, today),
                self.repository.save_asset_raw(asset.ticker, category, "bear_thesis", bear_res, today),
                self.repository.save_asset_raw(asset.ticker, category, "financials", fin_res, today),
                self.repository.save_asset_raw(asset.ticker, category, "news", news_res, today)
            )

            logger.info(f"[{asset.ticker}] Waiting for sector data ({asset.sector})...")
            sector_data = await sector_task

            # --- SYNTHESIS DISABLED TEMPORARILY (Pending Phase 3) ---
            # logger.info(f"[{asset.ticker}] Synthesizing...")
            # result = await self.provider.synthesize_report(...)
            # await self.repository.save_asset_final(...)
            # --------------------------------------------------------
            
            logger.info(f"[{asset.ticker}] Research completed (Synthesis pending refactor).")

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