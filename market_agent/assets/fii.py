from dataclasses import dataclass
from .base import Asset

@dataclass
class FIIAsset(Asset):
    @property
    def template_name(self) -> str:
        return "fii.j2"