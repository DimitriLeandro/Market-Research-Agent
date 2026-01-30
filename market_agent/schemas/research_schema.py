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

    class Config:
        json_schema_extra = {
            "example": {
                "ticker": "VALE3",
                "overall_sentiment": "Neutral",
                "sentiment_score": 0.1,
                "summary": "Vale is navigating...",
                "bullish_thesis": "The iron ore premium...",
                "bearish_thesis": "China demand remains...",
                "financial_analysis": "EBITDA margins compressed...",
                "news_and_events": "On Oct 15, the company announced..."
            }
        }