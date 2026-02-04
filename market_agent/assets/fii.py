from dataclasses import dataclass
from .base import Asset

@dataclass
class FIIAsset(Asset):
    @property
    def prompt_subdir(self) -> str:
        return "reits"