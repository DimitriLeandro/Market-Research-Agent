from typing import List, Optional
from pydantic import BaseModel, Field
from enum import Enum

class SentimentEnum(str, Enum):
    BULLISH = "Bullish"
    BEARISH = "Bearish"
    NEUTRAL = "Neutral"
    CAUTIOUS = "Cautious"

class TrendEnum(str, Enum):
    UPTREND = "Uptrend"
    DOWNTREND = "Downtrend"
    SIDEWAYS = "Sideways"
    VOLATILE = "Volatile"

class ResearchResult(BaseModel):
    ticker: str
    analysis_date: str
    overall_sentiment: SentimentEnum
    sentiment_score: float = Field(..., ge=-1.0, le=1.0, description="-1.0 to 1.0")
    price_trend: TrendEnum
    
    summary: str = Field(..., description="High-level executive summary of the asset status.")
    bullish_thesis: str = Field(..., description="Detailed positive drivers and upside arguments.")
    bearish_thesis: str = Field(..., description="Detailed risks and downside arguments.")
    financial_analysis: str = Field(..., description="Analysis of revenues, margins, and balance sheet trends.")
    news_and_events: str = Field(..., description="Chronological synthesis of recent material events.")

class SectorResult(BaseModel):
    sector: str
    analysis_date: str
    overall_sentiment: SentimentEnum
    
    summary: str = Field(..., description="High-level executive summary of the sector context.")
    bullish_thesis: str = Field(..., description="Consolidated positive drivers for the sector.")
    bearish_thesis: str = Field(..., description="Consolidated risks and headwinds for the sector.")
    news_and_events: str = Field(..., description="Key sector-wide news and regulatory changes.")