import json
import re
import asyncio
import logging
from google import genai
from google.genai import types
from google.genai.errors import ClientError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, before_sleep_log

from ..config.settings import Config
from ..assets.base import Asset
from ..schemas.research_schema import ResearchResult, SectorResult
from .interfaces import IResearchProvider
from .vectors import SearchVectorGenerator
from ..prompts.templates import TemplateManager

logger = logging.getLogger(__name__)

class GeminiProvider(IResearchProvider):
    def __init__(self, api_key: str, semaphore: asyncio.Semaphore):
        self.client = genai.Client(api_key=api_key)
        self.templates = TemplateManager()
        self.semaphore = semaphore

    def _clean_json(self, raw_text: str) -> str:
        cleaned = re.sub(r"```json\s*", "", raw_text)
        cleaned = re.sub(r"```", "", cleaned)
        return cleaned.strip()

    async def conduct_research(self, asset: Asset, context: dict) -> ResearchResult:
        raise NotImplementedError("Use specific research step methods.")

    @retry(
        retry=retry_if_exception_type(ClientError),
        stop=stop_after_attempt(10),
        wait=wait_exponential(multiplier=1, min=1, max=60),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    async def _execute_step(self, template_path: str, **kwargs) -> str:
        prompt = self.templates.render(template_path, **kwargs)
        
        async with self.semaphore:
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


    async def research_sector_bull(self, sector: str) -> str:
        queries = SearchVectorGenerator.get_sector_bull_queries(sector)
        return await self._execute_step("sectors/bull.j2", sector=sector, queries=queries)

    async def research_sector_bear(self, sector: str) -> str:
        queries = SearchVectorGenerator.get_sector_bear_queries(sector)
        return await self._execute_step("sectors/bear.j2", sector=sector, queries=queries)

    async def research_sector_news(self, sector: str) -> str:
        queries = SearchVectorGenerator.get_sector_news_queries(sector)
        return await self._execute_step("sectors/news.j2", sector=sector, queries=queries)


    async def research_asset_bull(self, asset: Asset) -> str:
        queries = SearchVectorGenerator.get_bull_queries(asset)
        return await self._execute_step(f"{asset.prompt_subdir}/bull.j2", ticker=asset.ticker, name=asset.name, queries=queries)

    async def research_asset_bear(self, asset: Asset) -> str:
        queries = SearchVectorGenerator.get_bear_queries(asset)
        return await self._execute_step(f"{asset.prompt_subdir}/bear.j2", ticker=asset.ticker, name=asset.name, queries=queries)

    async def research_asset_news(self, asset: Asset) -> str:
        queries = SearchVectorGenerator.get_news_queries(asset)
        return await self._execute_step(f"{asset.prompt_subdir}/news.j2", ticker=asset.ticker, name=asset.name, queries=queries)

    async def research_asset_financials(self, asset: Asset) -> str:
        queries = SearchVectorGenerator.get_financials_queries(asset)
        return await self._execute_step(f"{asset.prompt_subdir}/financials.j2", ticker=asset.ticker, name=asset.name, queries=queries)

    async def research_asset_filings(self, asset: Asset) -> str:
        queries = SearchVectorGenerator.get_filings_queries(asset)
        return await self._execute_step(f"{asset.prompt_subdir}/filings.j2", ticker=asset.ticker, name=asset.name, queries=queries)

    async def research_asset_earnings(self, asset: Asset) -> str:
        queries = SearchVectorGenerator.get_earnings_queries(asset)
        return await self._execute_step(f"{asset.prompt_subdir}/earnings.j2", ticker=asset.ticker, name=asset.name, queries=queries)

    async def research_asset_management(self, asset: Asset) -> str:
        queries = SearchVectorGenerator.get_management_queries(asset)
        return await self._execute_step(f"{asset.prompt_subdir}/management.j2", ticker=asset.ticker, name=asset.name, queries=queries)


    @retry(
        retry=retry_if_exception_type(ClientError),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=1, max=60),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    async def synthesize_analysis(self, template_path: str, context: dict) -> str:
        prompt = self.templates.render(template_path, **context)
        
        async with self.semaphore:
            def _call():
                return self.client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.4 
                    )
                )
            
            response = await asyncio.to_thread(_call)
            return response.text if response.text else "Synthesis failed."

    @retry(
        retry=retry_if_exception_type(ClientError),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=1, max=60),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    async def generate_json_report(self, category: str, context: dict, is_sector: bool = False) -> dict:
        """
        Transforms Markdown synthesis into structured JSON.
        category: 'stocks', 'reits', 'sectors'
        """
        template_path = f"{category}/reporting.j2" if not is_sector else "sectors/reporting.j2"
        prompt = self.templates.render(template_path, **context)
        
        schema = SectorResult if is_sector else ResearchResult

        async with self.semaphore:
            def _call():
                return self.client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.1,
                        response_mime_type="application/json",
                        response_schema=schema.model_json_schema(),
                    )
                )
            
            response = await asyncio.to_thread(_call)
            return json.loads(self._clean_json(response.text))