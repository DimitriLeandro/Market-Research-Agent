from datetime import date
from typing import List
from ..assets.base import Asset
from ..assets.fii import FIIAsset

class SearchVectorGenerator:
    @staticmethod
    def get_sector_queries(sector: str) -> List[str]:
        year = date.today().year
        return [
            f'perspectiva setor {sector} brasil {year} tendências',
            f'riscos regulatórios setor {sector} brasil {year}',
            f'impacto macroeconomia taxa selic setor {sector}'
        ]

    @staticmethod
    def get_fundamentals_queries(asset: Asset) -> List[str]:
        return [
            f'{asset.ticker} tese de investimento bull bear case',
            f'{asset.ticker} vantagens competitivas e riscos',
            f'{asset.ticker} estrutura de capital dívida e alavancagem'
        ]

    @staticmethod
    def get_financials_queries(asset: Asset) -> List[str]:
        year = date.today().year
        return [
            f'{asset.ticker} resultados trimestrais {year} destaques financeiros',
            f'{asset.ticker} guidance {year} ebitda receita',
            f'{asset.ticker} release de resultados últimos trimestres'
        ]

    @staticmethod
    def get_news_queries(asset: Asset) -> List[str]:
        year = date.today().year
        return [
            f'{asset.ticker} fatos relevantes CVM {year}',
            f'{asset.ticker} notícias corporativas processos judiciais recentes',
            f'{asset.ticker} recomendação compra venda bancos {year}'
        ]