import asyncio
import logging
from datetime import date
from typing import List

from .config.settings import Config
from .assets.base import Asset
from .assets.equity import EquityAsset
from .assets.fii import FIIAsset
from .research.provider import GeminiProvider
from .research.enrichment import YFinanceEnricher
from .persistence.repository import ResearchRepository
from .persistence.renderer import ReportRenderer

logger = logging.getLogger(__name__)

class MarketAgent:
    def __init__(self):
        # Dependency Injection via Constructor
        self.api_key = Config.load_api_key()
        self.provider = GeminiProvider(self.api_key)
        
        # Switched to Real YFinance Enricher
        self.enricher = YFinanceEnricher()
        
        self.repository = ResearchRepository(Config.RESULTS_DIR)
        self.assets = self._load_assets()
        
        # Rate Limiting: Set to 1 to prevent 429 RESOURCE_EXHAUSTED errors
        # This processes assets sequentially instead of in parallel bursts.
        self.semaphore = asyncio.Semaphore(1)

    def _load_assets(self) -> List[Asset]:
        raw = Config.load_portfolio()
        assets = []
        for item in raw:
            # Fix: Map YAML 'type' to class 'asset_type'
            # We create a copy to avoid modifying the original dict if used elsewhere
            asset_data = item.copy()
            asset_type_str = asset_data.pop('type') # Remove 'type' key
            asset_data['asset_type'] = asset_type_str # Add 'asset_type' key

            if asset_type_str == 'equity':
                assets.append(EquityAsset(**asset_data))
            elif asset_type_str == 'fii':
                assets.append(FIIAsset(**asset_data))
        return assets

    async def _process_single_asset(self, asset: Asset, today: date):
        async with self.semaphore: # Rate Limiter
            logger.info(f"Starting {asset.ticker}")
            try:
                # 1. Idempotency Check
                if self.repository.exists(asset.ticker, today):
                    logger.info(f"Skipping {asset.ticker} (Already exists)")
                    return

                # 2. Enrichment (Now fetches Real Data: Price, P/L, P/VP)
                context = await self.enricher.get_financial_data(asset)

                # 3. Research
                result = await self.provider.conduct_research(asset, context)

                # 4. Deterministic Date Assignment
                # Overwrite LLM-generated date with the actual execution date to prevent hallucinations.
                result.analysis_date = today.isoformat()

                # 5. Rendering
                report_md = ReportRenderer.render(result)

                # 6. Save
                self.repository.save(
                    asset.ticker, 
                    result.model_dump(mode='json'), 
                    report_md, 
                    today
                )
                logger.info(f"Completed {asset.ticker}")

            except Exception as e:
                logger.error(f"Failed to process {asset.ticker}: {e}", exc_info=True)

    async def run_cycle(self):
        today = date.today()
        # Removed logic to find previous date
        logger.info(f"Cycle Date: {today}")

        tasks = [
            self._process_single_asset(asset, today)
            for asset in self.assets
        ]
        
        await asyncio.gather(*tasks)