import asyncio
import logging
import subprocess
from datetime import date
from typing import List

from .config.settings import Config
from .assets.base import Asset
from .assets.equity import EquityAsset
from .assets.fii import FIIAsset
from .research.provider import GeminiProvider
from .research.enrichment import YFinanceEnricher
from .persistence.repository import ResearchRepository
# Renderer import removed - redundant artifact logic deleted

logger = logging.getLogger(__name__)

class MarketAgent:
    def __init__(self):
        self.api_key = Config.load_api_key()
        self.provider = GeminiProvider(self.api_key)
        self.enricher = YFinanceEnricher()
        self.repository = ResearchRepository(Config.RESULTS_DIR)
        self.assets = self._load_assets()
        # Strictly sequential to avoid Rate Limits (429)
        self.semaphore = asyncio.Semaphore(1)

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

    def _git_auto_commit(self):
        today_str = date.today().strftime("%Y-%m-%d")
        try:
            # 1. Add changes
            subprocess.run(["git", "add", "results/"], check=True)
            
            # 2. Commit
            commit_msg = f"docs: adding {today_str} results (auto commit)"
            subprocess.run(["git", "commit", "-m", commit_msg], check=True)
            
            # 3. Push
            subprocess.run(["git", "push"], check=True)
            logger.info(f"Git auto-commit successful: {commit_msg}")
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Git auto-commit failed: {e}")

    async def _process_single_asset(self, asset: Asset, today: date):
        async with self.semaphore:
            logger.info(f"=== Starting Pipeline for {asset.ticker} ===")
            try:
                if self.repository.exists(asset.ticker, today):
                    logger.info(f"Skipping {asset.ticker} (Already completed)")
                    return

                # 1. Sector Research
                sector_res = await self.provider.research_sector(asset)
                self.repository.save_raw(asset.ticker, "sector_analysis", sector_res, today)

                # 2. Fundamentals Research
                fund_res = await self.provider.research_fundamentals(asset)
                self.repository.save_raw(asset.ticker, "fundamentals", fund_res, today)

                # 3. Financials Research
                fin_res = await self.provider.research_financials(asset)
                self.repository.save_raw(asset.ticker, "financials", fin_res, today)

                # 4. News Research
                news_res = await self.provider.research_news(asset)
                self.repository.save_raw(asset.ticker, "news", news_res, today)

                # 5. Synthesis
                result = await self.provider.synthesize_report(
                    asset, 
                    sector=sector_res,
                    fundamentals=fund_res,
                    financials=fin_res,
                    news=news_res
                )

                # 6. Finalize (JSON ONLY)
                result.analysis_date = today.isoformat()
                
                # FIX: Removed 'report_md' argument to match new Repository signature
                self.repository.save_final(
                    asset.ticker, 
                    result.model_dump(mode='json'), 
                    today
                )
                logger.info(f"=== Completed {asset.ticker} ===")

            except Exception as e:
                logger.error(f"Failed to process {asset.ticker}: {e}", exc_info=True)

    async def run_cycle(self):
        today = date.today()
        logger.info(f"Cycle Date: {today}")
        tasks = [self._process_single_asset(asset, today) for asset in self.assets]
        await asyncio.gather(*tasks)
        
        # Trigger Git Auto-Commit after all tasks are done
        self._git_auto_commit()