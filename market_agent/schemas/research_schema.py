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

class ImpactEnum(str, Enum):
    POSITIVE = "Positive"
    NEGATIVE = "Negative"
    NEUTRAL = "Neutral"

class KeyEvent(BaseModel):
    event_name: str = Field(..., description="Short title of the event")
    impact: ImpactEnum
    description: str = Field(..., description="Concise explanation")
    source_type: str = Field(..., description="e.g. 'News', 'Official Filing', 'Rumor'")

class InvestmentThesis(BaseModel):
    bull_case: str = Field(..., description="Why should one buy?")
    bear_case: str = Field(..., description="Why should one sell?")

class ResearchResult(BaseModel):
    ticker: str
    analysis_date: str
    overall_sentiment: SentimentEnum
    sentiment_score: float = Field(..., ge=-1.0, le=1.0, description="-1.0 to 1.0")
    price_trend: TrendEnum
    key_events: List[KeyEvent]
    risk_factors: List[str]
    investment_thesis: InvestmentThesis
    summary_markdown: str = Field(..., description="Rich markdown summary for humans")

    class Config:
        json_schema_extra = {
            "example": {
                "ticker": "VALE3",
                "overall_sentiment": "Neutral",
                "sentiment_score": 0.1,
                "summary_markdown": "## Summary\n..."
            }
        }