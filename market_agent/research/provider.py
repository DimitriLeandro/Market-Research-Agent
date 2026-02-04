import json
import re
import asyncio
import logging
from google import genai
from google.genai import types
from google.genai.errors import ClientError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ..config.settings import Config
from ..assets.base import Asset
from ..schemas.research_schema import ResearchResult
from .interfaces import IResearchProvider
from .vectors import SearchVectorGenerator
from ..prompts.templates import TemplateManager

logger = logging.getLogger(__name__)

class GeminiProvider(IResearchProvider):
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.templates = TemplateManager()

    def _clean_json(self, raw_text: str) -> str:
        cleaned = re.sub(r"```json\s*", "", raw_text)
        cleaned = re.sub(r"```", "", cleaned)
        return cleaned.strip()

    async def conduct_research(self, asset: Asset, context: dict) -> ResearchResult:
        raise NotImplementedError("Use specific research step methods.")

    @retry(retry=retry_if_exception_type(ClientError), stop=stop_after_attempt(5), wait=wait_exponential(multiplier=2, min=4, max=60))
    async def _execute_step(self, template_path: str, **kwargs) -> str:
        # Template manager now expects a path relative to PROMPTS_DIR, e.g., "stocks/bull.j2"
        prompt = self.templates.render(template_path, **kwargs)
        
        def _call():
            return self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    tools=[types.Tool(google_search=types.GoogleSearch())]
                )
            )
        
        response = await asyncio.to_thread(_call)
        return response.text if response.text else "No data found."

    # --- SECTOR RESEARCH ---

    async def research_sector_bull(self, sector: str) -> str:
        logger.info(f"Sector Bull: {sector}")
        queries = SearchVectorGenerator.get_sector_bull_queries(sector)
        return await self._execute_step("sectors/bull.j2", sector=sector, queries=queries)

    async def research_sector_bear(self, sector: str) -> str:
        logger.info(f"Sector Bear: {sector}")
        queries = SearchVectorGenerator.get_sector_bear_queries(sector)
        return await self._execute_step("sectors/bear.j2", sector=sector, queries=queries)

    async def research_sector_news(self, sector: str) -> str:
        logger.info(f"Sector News: {sector}")
        queries = SearchVectorGenerator.get_sector_news_queries(sector)
        return await self._execute_step("sectors/news.j2", sector=sector, queries=queries)

    # --- ASSET RESEARCH ---

    async def research_asset_bull(self, asset: Asset) -> str:
        logger.info(f"Asset Bull: {asset.ticker}")
        queries = SearchVectorGenerator.get_bull_queries(asset)
        # Dynamic path: stocks/bull.j2 or reits/bull.j2
        return await self._execute_step(f"{asset.prompt_subdir}/bull.j2", ticker=asset.ticker, name=asset.name, queries=queries)

    async def research_asset_bear(self, asset: Asset) -> str:
        logger.info(f"Asset Bear: {asset.ticker}")
        queries = SearchVectorGenerator.get_bear_queries(asset)
        return await self._execute_step(f"{asset.prompt_subdir}/bear.j2", ticker=asset.ticker, name=asset.name, queries=queries)

    async def research_asset_news(self, asset: Asset) -> str:
        logger.info(f"Asset News: {asset.ticker}")
        queries = SearchVectorGenerator.get_news_queries(asset)
        return await self._execute_step(f"{asset.prompt_subdir}/news.j2", ticker=asset.ticker, name=asset.name, queries=queries)

    async def research_asset_financials(self, asset: Asset) -> str:
        logger.info(f"Asset Financials: {asset.ticker}")
        queries = SearchVectorGenerator.get_financials_queries(asset)
        return await self._execute_step(f"{asset.prompt_subdir}/financials.j2", ticker=asset.ticker, name=asset.name, queries=queries)

    # --- SYNTHESIS ---

    async def synthesize_report(self, asset: Asset, sector_data: dict, bull: str, bear: str, news: str, financials: str) -> ResearchResult:
        logger.info(f"Synthesizing: {asset.ticker}")
        
        prompt = self.templates.render(
            "common/synthesis.j2", # We use a common synthesis template that can handle the inputs
            ticker=asset.ticker,
            sector_bull=sector_data.get('bull_thesis'),
            sector_bear=sector_data.get('bear_thesis'),
            sector_news=sector_data.get('news'),
            asset_bull=bull,
            asset_bear=bear,
            asset_news=news,
            asset_financials=financials
        )

        @retry(retry=retry_if_exception_type(ClientError), stop=stop_after_attempt(5), wait=wait_exponential(multiplier=2, min=4, max=60))
        def _call_synthesis():
            return self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    response_mime_type="application/json",
                    response_schema=ResearchResult.model_json_schema(),
                )
            )

        response = await asyncio.to_thread(_call_synthesis)
        data = json.loads(self._clean_json(response.text))
        return ResearchResult(**data)