import asyncio
import logging
import subprocess
import time
from datetime import date
from typing import List, Set, Dict, Any

from .config.settings import Config
from .assets.base import Asset
from .assets.equity import EquityAsset
from .assets.fii import FIIAsset
from .research.provider import GeminiProvider
from .research.enrichment import YFinanceEnricher
from .persistence.repository import ResearchRepository

logger = logging.getLogger(__name__)

class MarketAgent:
    def __init__(self, test_mode: bool = False):
        self.test_mode = test_mode
        self.api_key = Config.load_api_key()
        
        # We pass the semaphore to the provider so it can throttle itself globally
        self.global_semaphore = asyncio.Semaphore(Config.MAX_CONCURRENT_REQUESTS)
        self.provider = GeminiProvider(self.api_key, self.global_semaphore)
        
        self.enricher = YFinanceEnricher()
        self.repository = ResearchRepository(Config.RESULTS_DIR)
        
        self.assets = self._load_assets()

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
            elif asset_type_str == 'fii':
                assets.append(FIIAsset(**asset_data))
        return assets

    def _get_unique_sectors(self) -> Set[str]:
        return set(asset.sector for asset in self.assets)

    async def _process_sector(self, sector: str, today: date) -> Dict[str, str]:
        """
        Processes a sector: Checks cache, runs research steps in parallel, returns data map.
        """
        logger.info(f"[{sector}] Starting Sector Pipeline...")
        try:
            # 1. Check if fully exists
            if await self.repository.sector_exists(sector, today):
                logger.info(f"[{sector}] Loaded from cache.")
                return await self.repository.load_sector_research(sector, today)

            # 2. Run research steps in parallel
            # The provider uses the global semaphore, so we can just fire these off
            t_bull = self.provider.research_sector_bull(sector)
            t_bear = self.provider.research_sector_bear(sector)
            t_news = self.provider.research_sector_news(sector)

            # Gather results
            bull, bear, news = await asyncio.gather(t_bull, t_bear, t_news)

            # 3. Save results (Async I/O)
            await self.repository.save_sector_research(sector, "bull_thesis", bull, today)
            await self.repository.save_sector_research(sector, "bear_thesis", bear, today)
            await self.repository.save_sector_research(sector, "news", news, today)
            
            logger.info(f"[{sector}] Completed.")
            
            return {
                "bull_thesis": bull,
                "bear_thesis": bear,
                "news": news
            }

        except Exception as e:
            logger.error(f"[{sector}] Failed: {e}", exc_info=True)
            # Return empty data so dependent assets don't crash, but log the error
            return {"bull_thesis": "Error", "bear_thesis": "Error", "news": "Error"}

    async def _process_asset(self, asset: Asset, sector_task: asyncio.Task, today: date):
        """
        Processes an asset. Runs asset research in parallel with sector research.
        Waits for sector data only before synthesis.
        """
        logger.info(f"[{asset.ticker}] Starting Asset Pipeline...")
        try:
            if await self.repository.asset_exists(asset.ticker, today):
                logger.info(f"[{asset.ticker}] Loaded from cache.")
                # We still await the sector task to ensure the graph completes cleanly
                await sector_task 
                return

            # 1. Run independent asset research steps in parallel
            # These do NOT depend on the sector, so we run them immediately
            t_bull = self.provider.research_asset_bull(asset)
            t_bear = self.provider.research_asset_bear(asset)
            t_fin = self.provider.research_asset_financials(asset)
            t_news = self.provider.research_asset_news(asset)

            bull_res, bear_res, fin_res, news_res = await asyncio.gather(
                t_bull, t_bear, t_fin, t_news
            )

            # 2. Save Raw Data
            await asyncio.gather(
                self.repository.save_asset_raw(asset.ticker, "bull_thesis", bull_res, today),
                self.repository.save_asset_raw(asset.ticker, "bear_thesis", bear_res, today),
                self.repository.save_asset_raw(asset.ticker, "financials", fin_res, today),
                self.repository.save_asset_raw(asset.ticker, "news", news_res, today)
            )

            # 3. Wait for Sector Data (Dependency for Synthesis)
            logger.info(f"[{asset.ticker}] Waiting for sector data ({asset.sector})...")
            sector_data = await sector_task

            # 4. Synthesize
            result = await self.provider.synthesize_report(
                asset, 
                sector_data=sector_data,
                bull=bull_res,
                bear=bear_res,
                financials=fin_res,
                news=news_res
            )

            result.analysis_date = today.isoformat()
            
            await self.repository.save_asset_final(
                asset.ticker, 
                result.model_dump(mode='json'), 
                today
            )
            logger.info(f"[{asset.ticker}] Completed.")

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

        # 1. Create Sector Tasks (Map: SectorName -> Task)
        # We start these immediately. They will run in the background.
        unique_sectors = self._get_unique_sectors()
        sector_tasks_map: Dict[str, asyncio.Task] = {}
        
        for sector in unique_sectors:
            task = asyncio.create_task(self._process_sector(sector, today))
            sector_tasks_map[sector] = task

        # 2. Create Asset Tasks
        # Each asset task takes a reference to its specific sector task
        asset_tasks = []
        for asset in self.assets:
            if asset.sector not in sector_tasks_map:
                logger.error(f"Asset {asset.ticker} has unknown sector {asset.sector}. Skipping.")
                continue
            
            sec_task = sector_tasks_map[asset.sector]
            task = asyncio.create_task(self._process_asset(asset, sec_task, today))
            asset_tasks.append(task)

        # 3. Wait for ALL tasks to complete
        # Note: We await asset_tasks. Asset tasks inherently await their sector tasks 
        # before finishing. However, we also await sector_tasks_map.values() ensures 
        # orphan sectors (if any) also finish, though functionally redundant if mapped correctly.
        
        all_tasks = list(sector_tasks_map.values()) + asset_tasks
        if all_tasks:
            logger.info(f"Scheduled {len(sector_tasks_map)} sectors and {len(asset_tasks)} assets. Running...")
            await asyncio.gather(*all_tasks)
        
        logger.info("All research tasks finished.")
        self._git_auto_commit()