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

class Section(BaseModel):
    id: str = Field(..., description="Unique identifier for the section (e.g., 'bull_thesis', 'financials').")
    title: str = Field(..., description="Display title for the section.")
    content: str = Field(..., description="Markdown content for this section.")

class ResearchResult(BaseModel):
    ticker: str
    analysis_date: str
    overall_sentiment: SentimentEnum
    sentiment_score: float = Field(..., ge=-1.0, le=1.0, description="-1.0 to 1.0")
    price_trend: TrendEnum
    
    # Flexible sections replacing fixed fields
    sections: List[Section] = Field(..., description="Dynamic list of report sections.")

class SectorResult(BaseModel):
    sector: str
    analysis_date: str
    overall_sentiment: SentimentEnum
    
    # Flexible sections replacing fixed fields
    sections: List[Section] = Field(..., description="Dynamic list of sector report sections.")