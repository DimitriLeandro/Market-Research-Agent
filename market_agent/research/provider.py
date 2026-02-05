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


    async def synthesize_report(self, asset: Asset, sector_data: dict, bull: str, bear: str, news: str, financials: str) -> ResearchResult:
        prompt = self.templates.render(
            "common/synthesis.j2",
            ticker=asset.ticker,
            sector_bull=sector_data.get('bull_thesis'),
            sector_bear=sector_data.get('bear_thesis'),
            sector_news=sector_data.get('news'),
            asset_bull=bull,
            asset_bear=bear,
            asset_news=news,
            asset_financials=financials
        )

        @retry(
            retry=retry_if_exception_type(ClientError),
            stop=stop_after_attempt(10),
            wait=wait_exponential(multiplier=1, min=1, max=60),
            before_sleep=before_sleep_log(logger, logging.WARNING)
        )
        async def _call_synthesis():
            async with self.semaphore:
                def _inner_call():
                    return self.client.models.generate_content(
                        model="gemini-2.0-flash",
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            temperature=0.1,
                            response_mime_type="application/json",
                            response_schema=ResearchResult.model_json_schema(),
                        )
                    )
                response = await asyncio.to_thread(_inner_call)
                return response

        response = await _call_synthesis()
        data = json.loads(self._clean_json(response.text))
        return ResearchResult(**data)

    async def synthesize_sector_report(self, sector: str, bull: str, bear: str, news: str) -> SectorResult:
        prompt = self.templates.render(
            "sectors/synthesis.j2",
            sector=sector,
            bull=bull,
            bear=bear,
            news=news
        )

        @retry(
            retry=retry_if_exception_type(ClientError),
            stop=stop_after_attempt(10),
            wait=wait_exponential(multiplier=1, min=1, max=60),
            before_sleep=before_sleep_log(logger, logging.WARNING)
        )
        async def _call_sector_synthesis():
            async with self.semaphore:
                def _inner_call():
                    return self.client.models.generate_content(
                        model="gemini-2.0-flash",
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            temperature=0.1,
                            response_mime_type="application/json",
                            response_schema=SectorResult.model_json_schema(),
                        )
                    )
                response = await asyncio.to_thread(_inner_call)
                return response

        response = await _call_sector_synthesis()
        data = json.loads(self._clean_json(response.text))
        return SectorResult(**data)