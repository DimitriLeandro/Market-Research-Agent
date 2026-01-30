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
        # NOTE: This single method is deprecated in the new flow but kept for interface compatibility.
        # Ideally, the Agent should call specific methods below.
        raise NotImplementedError("Use specific research step methods.")

    @retry(retry=retry_if_exception_type(ClientError), stop=stop_after_attempt(5), wait=wait_exponential(multiplier=2, min=4, max=60))
    async def _execute_step(self, template_name: str, **kwargs) -> str:
        prompt = self.templates.render(template_name, **kwargs)
        
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

    async def research_sector(self, asset: Asset) -> str:
        logger.info(f"Researching Sector: {asset.sector}")
        queries = SearchVectorGenerator.get_sector_queries(asset.sector)
        return await self._execute_step("sector.j2", sector=asset.sector, name=asset.name, queries=queries)

    async def research_fundamentals(self, asset: Asset) -> str:
        logger.info(f"Researching Fundamentals: {asset.ticker}")
        queries = SearchVectorGenerator.get_fundamentals_queries(asset)
        return await self._execute_step("fundamentals.j2", ticker=asset.ticker, name=asset.name, queries=queries)

    async def research_financials(self, asset: Asset) -> str:
        logger.info(f"Researching Financials: {asset.ticker}")
        queries = SearchVectorGenerator.get_financials_queries(asset)
        return await self._execute_step("financials.j2", ticker=asset.ticker, name=asset.name, queries=queries)

    async def research_news(self, asset: Asset) -> str:
        logger.info(f"Researching News: {asset.ticker}")
        queries = SearchVectorGenerator.get_news_queries(asset)
        return await self._execute_step("news.j2", ticker=asset.ticker, name=asset.name, queries=queries)

    async def synthesize_report(self, asset: Asset, sector: str, fundamentals: str, financials: str, news: str) -> ResearchResult:
        logger.info(f"Synthesizing Final Report: {asset.ticker}")
        
        prompt = self.templates.render(
            "synthesis.j2",
            sector_data=sector,
            fundamentals_data=fundamentals,
            financials_data=financials,
            news_data=news
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