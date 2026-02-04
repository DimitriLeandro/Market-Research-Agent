from datetime import date
from typing import List
from ..assets.base import Asset

class SearchVectorGenerator:
    @staticmethod
    def _get_year() -> int:
        return date.today().year

    # --- SECTOR VECTORS ---

    @staticmethod
    def get_sector_bull_queries(sector: str) -> List[str]:
        y = SearchVectorGenerator._get_year()
        return [
            f'setor {sector} brasil {y} tendências crescimento',
            f'fatores macroeconomicos positivos setor {sector} brasil',
            f'oportunidades investimento setor {sector} {y} relatórios bancos',
            f'preço commodities impacto positivo {sector} brasil'
        ]

    @staticmethod
    def get_sector_bear_queries(sector: str) -> List[str]:
        y = SearchVectorGenerator._get_year()
        return [
            f'riscos regulatórios setor {sector} brasil {y}',
            f'desafios operacionais setor {sector} brasil curto prazo',
            f'aumento custo capital endividamento setor {sector} brasil',
            f'impacto inflação e juros setor {sector} analise'
        ]

    @staticmethod
    def get_sector_news_queries(sector: str) -> List[str]:
        y = SearchVectorGenerator._get_year()
        return [
            f'notícias recentes setor {sector} brasil últimos 30 dias',
            f'mudanças legislação {sector} brasil {y}',
            f'fusões aquisições setor {sector} brasil recentes'
        ]

    # --- ASSET VECTORS ---

    @staticmethod
    def get_bull_queries(asset: Asset) -> List[str]:
        return [
            f'{asset.ticker} tese de investimento bull case compra',
            f'{asset.ticker} vantagens competitivas fosso economico',
            f'{asset.ticker} projetos expansão crescimento receita',
            f'{asset.ticker} recomendação bancos compra preço alvo'
        ]

    @staticmethod
    def get_bear_queries(asset: Asset) -> List[str]:
        return [
            f'{asset.ticker} riscos tese investimento bear case',
            f'{asset.ticker} endividamento alavancagem riscos',
            f'{asset.ticker} perda market share concorrência',
            f'{asset.ticker} pontos negativos analise fundamentalista'
        ]

    @staticmethod
    def get_news_queries(asset: Asset) -> List[str]:
        y = SearchVectorGenerator._get_year()
        return [
            f'{asset.ticker} fatos relevantes CVM {y} últimos 90 dias',
            f'{asset.ticker} processos judiciais passivos contingentes',
            f'{asset.ticker} notícias corporativas recentes',
            f'{asset.ticker} resultados trimestrais repercussão mercado'
        ]

    @staticmethod
    def get_financials_queries(asset: Asset) -> List[str]:
        y = SearchVectorGenerator._get_year()
        return [
            f'{asset.ticker} release resultados trimestrais {y} tabela',
            f'{asset.ticker} evolução ebitda lucro liquido receita',
            f'{asset.ticker} fluxo caixa livre capex guidance'
        ]