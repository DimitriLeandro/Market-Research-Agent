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
        """Removes markdown fences and extra whitespace."""
        cleaned = re.sub(r"```json\s*", "", raw_text)
        cleaned = re.sub(r"```", "", cleaned)
        return cleaned.strip()

    async def conduct_research(self, asset: Asset, context: dict) -> ResearchResult:
        queries = SearchVectorGenerator.get_queries(asset)
        
        # ---------------------------------------------------------
        # PHASE 1: Data Collection (High Recall, "Data Hoarder" Persona)
        # ---------------------------------------------------------
        logger.info(f"Phase 1: Researching {asset.ticker} (Google Search)...")
        
        prompt_content = self.templates.render(
            asset.template_name,
            ticker=asset.ticker,
            name=asset.name,
            financial_data=context,
            queries=queries
        )

        @retry(
            retry=retry_if_exception_type(ClientError),
            stop=stop_after_attempt(5),
            wait=wait_exponential(multiplier=1, min=4, max=60),
            reraise=True
        )
        def _call_research():
            return self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt_content,
                config=types.GenerateContentConfig(
                    temperature=0.2, # Low temp for factual extraction
                    tools=[types.Tool(google_search=types.GoogleSearch())]
                )
            )

        try:
            research_response = await asyncio.to_thread(_call_research)
            
            if not research_response.text:
                raise ValueError(f"Empty response from Research Phase for {asset.ticker}")
                
            raw_findings = research_response.text

        except Exception as e:
            logger.error(f"Phase 1 Failed for {asset.ticker}: {str(e)}")
            raise e

        # ---------------------------------------------------------
        # PHASE 2: Structuring & Synthesis (High Precision, "Analyst" Persona)
        # ---------------------------------------------------------
        logger.info(f"Phase 2: Structuring Data for {asset.ticker} (Schema Enforcement)...")

        structuring_prompt = f"""
        You are a Senior Equity Analyst.
        
        INPUT DATA (Raw Intelligence Log):
        {raw_findings}
        
        TASK:
        Synthesize this raw data into a professional JSON Report.
        
        RULES FOR SYNTHESIS:
        1. **Eliminate Noise**: If a point is generic (e.g., "Monitor the market"), DELETE IT.
        2. **Grounding**: Every claim in 'summary_markdown' must be backed by a specific entity, number, or date found in the input.
        3. **Tone**: Direct, professional, and dense. No introductions.
        4. **Schema**: Map the sentiment strictly based on the *recent* news found.
        
        Output ONLY valid JSON.
        """

        @retry(
            retry=retry_if_exception_type(ClientError),
            stop=stop_after_attempt(5),
            wait=wait_exponential(multiplier=1, min=4, max=60),
            reraise=True
        )
        def _call_structure():
            return self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=structuring_prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    response_mime_type="application/json",
                    response_schema=ResearchResult.model_json_schema(),
                )
            )

        try:
            structure_response = await asyncio.to_thread(_call_structure)
            
            if not structure_response.text:
                raise ValueError(f"Empty response from Structuring Phase for {asset.ticker}")

            cleaned_json = self._clean_json(structure_response.text)
            data_dict = json.loads(cleaned_json)
            
            return ResearchResult(**data_dict)

        except json.JSONDecodeError as e:
            logger.error(f"JSON Parse Error for {asset.ticker}: {structure_response.text}")
            raise e
        except Exception as e:
            logger.error(f"Phase 2 Failed for {asset.ticker}: {str(e)}")
            raise e