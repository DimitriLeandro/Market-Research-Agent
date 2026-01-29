from dataclasses import dataclass
from .base import Asset

@dataclass
class EquityAsset(Asset):
    @property
    def template_name(self) -> str:
        return "equity.j2"