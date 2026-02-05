from dataclasses import dataclass
from .base import Asset

@dataclass
class SectorAsset(Asset):
    @property
    def prompt_subdir(self) -> str:
        return "sectors"