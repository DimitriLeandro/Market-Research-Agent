from datetime import date
from typing import List
from ..assets.base import Asset
from ..assets.fii import FIIAsset

class SearchVectorGenerator:
    @staticmethod
    def get_queries(asset: Asset) -> List[str]:
        current_year = date.today().year
        
        # 1. Fundamental & Regulatory (Base)
        queries = [
            f'{asset.ticker} "{asset.name}" fatos relevantes CVM {current_year}',
            f'{asset.ticker} resultados trimestrais {current_year} destaques',
            f'{asset.ticker} transcrição teleconferência de resultados {current_year}',
            f'{asset.ticker} recomendação bancos casas de análise {current_year}',
            f'{asset.ticker} riscos legais processos judiciais recentes'
        ]

        # 2. Asset-Specific Deep Dives
        if isinstance(asset, FIIAsset):
            queries.extend([
                f'{asset.ticker} relatório gerencial {current_year} vacância inadimplência',
                f'{asset.ticker} yield on cost dividend guidance {current_year}',
                f'{asset.ticker} reavaliação patrimonial imóveis {current_year}',
                f'{asset.ticker} pipeline de aquisições e vendas'
            ])
        else:
            # For Equities, we try to guess the sector context based on common terms
            queries.extend([
                f'{asset.ticker} guidance produção e capex {current_year}',
                f'{asset.ticker} fusões e aquisições rumores {current_year}',
                f'{asset.ticker} valuation múltiplo histórico vs pares',
                f'{asset.ticker} drivers macroeconômicos impacto setor'
            ])
            
        return queries