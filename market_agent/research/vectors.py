from datetime import date
from typing import List
from ..assets.base import Asset

class SearchVectorGenerator:
    @staticmethod
    def _get_year() -> int:
        return date.today().year

    @staticmethod
    def _get_time_context() -> str:
        """Returns a string for recent context constraints."""
        return "últimos 90 dias"

    @staticmethod
    def get_sector_bull_queries(sector: str) -> List[str]:
        y = SearchVectorGenerator._get_year()
        return [
            f'setor {sector} brasil {y} perspectivas positivas e oportunidades crescimento',
            f'relatórios bancos investimento setor {sector} brasil {y} recomendações compra',
            f'fatores macroeconômicos favoráveis setor {sector} brasil atual',
            f'tendências inovação e aumento demanda setor {sector} brasil'
        ]

    @staticmethod
    def get_sector_bear_queries(sector: str) -> List[str]:
        y = SearchVectorGenerator._get_year()
        return [
            f'principais riscos e ameaças setor {sector} brasil {y}',
            f'impacto aumento juros e inflação custos setor {sector} brasil',
            f'mudanças regulatórias negativas e riscos fiscais setor {sector} brasil',
            f'desafios operacionais gargalos logísticos setor {sector} brasil'
        ]

    @staticmethod
    def get_sector_news_queries(sector: str) -> List[str]:
        y = SearchVectorGenerator._get_year()
        recent = SearchVectorGenerator._get_time_context()
        return [
            f'notícias importantes setor {sector} brasil {recent}',
            f'fusões aquisições e consolidação setor {sector} brasil {y}',
            f'greves acidentes ou crises setor {sector} brasil {recent}',
            f'nova legislação e regulação setor {sector} brasil {recent}'
        ]

    @staticmethod
    def get_bull_queries(asset: Asset) -> List[str]:
        y = SearchVectorGenerator._get_year()
        return [
            f'{asset.ticker} tese de investimento compra pontos positivos',
            f'{asset.ticker} vantagens competitivas e diferenciais mercado',
            f'{asset.ticker} preço alvo e recomendações analistas {y}',
            f'{asset.ticker} projetos expansão e guidance {y}'
        ]

    @staticmethod
    def get_bear_queries(asset: Asset) -> List[str]:
        y = SearchVectorGenerator._get_year()
        return [
            f'{asset.ticker} riscos tese de investimento pontos negativos',
            f'{asset.ticker} desafios operacionais e financeiros {y}',
            f'{asset.ticker} rebaixamento recomendação analistas venda',
            f'{asset.ticker} concorrência e perda market share'
        ]

    @staticmethod
    def get_news_queries(asset: Asset) -> List[str]:
        recent = SearchVectorGenerator._get_time_context()
        return [
            f'{asset.ticker} notícias corporativas e escândalos {recent}',
            f'{asset.ticker} repercussão na mídia resultados {recent}',
            f'{asset.ticker} processos judiciais e passivos recentes',
            f'{asset.ticker} opinião analistas e colunistas mercado'
        ]

    @staticmethod
    def get_financials_queries(asset: Asset) -> List[str]:
        y = SearchVectorGenerator._get_year()
        return [
            f'{asset.ticker} tabela indicadores financeiros {y}',
            f'{asset.ticker} evolução margem ebitda e lucro líquido histórico',
            f'{asset.ticker} balanço patrimonial e fluxo de caixa {y}',
            f'{asset.ticker} histórico dividendos e payout'
        ]

    @staticmethod
    def get_filings_queries(asset: Asset) -> List[str]:
        y = SearchVectorGenerator._get_year()
        recent = SearchVectorGenerator._get_time_context()
        return [
            f'{asset.ticker} fatos relevantes CVM {recent}',
            f'{asset.ticker} comunicados ao mercado dividendos {y}',
            f'{asset.ticker} mudança composição acionária {recent}',
            f'{asset.ticker} atas assembleias e reuniões conselho {y}'
        ]

    @staticmethod
    def get_earnings_queries(asset: Asset) -> List[str]:
        y = SearchVectorGenerator._get_year()
        return [
            f'{asset.ticker} release de resultados trimestrais {y} pdf',
            f'{asset.ticker} destaques teleconferência resultados {y}',
            f'{asset.ticker} apresentação institucional investidores {y}',
            f'{asset.ticker} guidance e perspectivas administração {y}'
        ]

    @staticmethod
    def get_management_queries(asset: Asset) -> List[str]:
        y = SearchVectorGenerator._get_year()
        return [
            f'{asset.ticker} relatório gerencial mensal recente {y} pdf',
            f'{asset.ticker} comentário do gestor performance mensal',
            f'{asset.ticker} detalhamento carteira ativos relatório gerencial',
            f'{asset.ticker} cronograma amortização dívida relatório gerencial'
        ]