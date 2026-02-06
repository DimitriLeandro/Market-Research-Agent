from abc import ABC, abstractmethod
from typing import Dict, Any
from ..assets.base import Asset
from ..schemas.research_schema import ResearchResult

class IFinancialEnricher(ABC):
    @abstractmethod
    async def get_financial_data(self, asset: Asset) -> Dict[str, Any]:
        pass

class IResearchProvider(ABC):
    pass