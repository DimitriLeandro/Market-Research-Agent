import asyncio
import logging
import subprocess
from datetime import date
from typing import List, Set

from .config.settings import Config
from .assets.base import Asset
from .assets.equity import EquityAsset
from .assets.fii import FIIAsset
from .research.provider import GeminiProvider
from .research.enrichment import YFinanceEnricher
from .persistence.repository import ResearchRepository

logger = logging.getLogger(__name__)

class MarketAgent:
    def __init__(self):
        self.api_key = Config.load_api_key()
        self.provider = GeminiProvider(self.api_key)
        self.enricher = YFinanceEnricher()
        self.repository = ResearchRepository(Config.RESULTS_DIR)
        self.assets = self._load_assets()
        self.semaphore = asyncio.Semaphore(1) # Limit concurrency to avoid rate limits

    def _load_assets(self) -> List[Asset]:
        raw = Config.load_portfolio()
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

    async def _process_sector(self, sector: str, today: date):
        async with self.semaphore:
            logger.info(f"=== Starting Sector Pipeline for {sector} ===")
            try:
                if self.repository.sector_exists(sector, today):
                    logger.info(f"Skipping Sector {sector} (Already completed)")
                    return

                # Execute 3 distinct sector steps
                bull = await self.provider.research_sector_bull(sector)
                self.repository.save_sector_research(sector, "bull_thesis", bull, today)

                bear = await self.provider.research_sector_bear(sector)
                self.repository.save_sector_research(sector, "bear_thesis", bear, today)

                news = await self.provider.research_sector_news(sector)
                self.repository.save_sector_research(sector, "news", news, today)
                
                logger.info(f"=== Completed Sector {sector} ===")
            except Exception as e:
                logger.error(f"Failed to process sector {sector}: {e}", exc_info=True)

    async def _process_asset(self, asset: Asset, today: date):
        async with self.semaphore:
            logger.info(f"=== Starting Asset Pipeline for {asset.ticker} ===")
            try:
                if self.repository.asset_exists(asset.ticker, today):
                    logger.info(f"Skipping {asset.ticker} (Already completed)")
                    return

                # Load pre-computed sector data
                sector_data = self.repository.load_sector_research(asset.sector, today)

                # Asset specific research
                bull_res = await self.provider.research_asset_bull(asset)
                self.repository.save_asset_raw(asset.ticker, "bull_thesis", bull_res, today)

                bear_res = await self.provider.research_asset_bear(asset)
                self.repository.save_asset_raw(asset.ticker, "bear_thesis", bear_res, today)

                fin_res = await self.provider.research_asset_financials(asset)
                self.repository.save_asset_raw(asset.ticker, "financials", fin_res, today)

                news_res = await self.provider.research_asset_news(asset)
                self.repository.save_asset_raw(asset.ticker, "news", news_res, today)

                # Synthesis
                result = await self.provider.synthesize_report(
                    asset, 
                    sector_data=sector_data,
                    bull=bull_res,
                    bear=bear_res,
                    financials=fin_res,
                    news=news_res
                )

                result.analysis_date = today.isoformat()
                
                self.repository.save_asset_final(
                    asset.ticker, 
                    result.model_dump(mode='json'), 
                    today
                )
                logger.info(f"=== Completed Asset {asset.ticker} ===")

            except Exception as e:
                logger.error(f"Failed to process asset {asset.ticker}: {e}", exc_info=True)

    def _git_auto_commit(self):
        today_str = date.today().strftime("%Y-%m-%d")
        try:
            subprocess.run(["git", "add", "results/"], check=True)
            commit_msg = f"docs: adding {today_str} results (auto commit)"
            subprocess.run(["git", "commit", "-m", commit_msg], check=True)
            subprocess.run(["git", "push"], check=True)
            logger.info(f"Git auto-commit successful: {commit_msg}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Git auto-commit failed: {e}")

    async def run_cycle(self):
        today = date.today()
        logger.info(f"Cycle Date: {today}")

        # Phase 1: Sectors
        sectors = self._get_unique_sectors()
        sector_tasks = [self._process_sector(sector, today) for sector in sectors]
        if sector_tasks:
            await asyncio.gather(*sector_tasks)

        # Phase 2: Assets
        asset_tasks = [self._process_asset(asset, today) for asset in self.assets]
        if asset_tasks:
            await asyncio.gather(*asset_tasks)
        
        self._git_auto_commit()