from dataclasses import dataclass
from .base import Asset

@dataclass
class EquityAsset(Asset):
    @property
    def prompt_subdir(self) -> str:
        return "stocks"