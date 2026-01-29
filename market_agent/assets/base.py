from dataclasses import dataclass
from abc import ABC, abstractmethod

@dataclass
class Asset(ABC):
    ticker: str
    name: str
    asset_type: str
    sector: str

    @property
    @abstractmethod
    def template_name(self) -> str:
        pass