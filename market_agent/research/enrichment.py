import asyncio
import logging
import yfinance as yf
from typing import Dict, Any

from ..assets.base import Asset
from ..assets.equity import EquityAsset
from ..assets.reit import REITAsset
from .interfaces import IFinancialEnricher

logger = logging.getLogger(__name__)

class YFinanceEnricher(IFinancialEnricher):
    """
    Fetches live financial data using yfinance.
    Enforces specific data points per asset type:
    - Equity: Price, P/L, P/VP
    - REIT: Price, P/VP
    """
    async def get_financial_data(self, asset: Asset) -> Dict[str, Any]:
        return await asyncio.to_thread(self._fetch_sync, asset)

    def _fetch_sync(self, asset: Asset) -> Dict[str, Any]:
        ticker_symbol = asset.ticker if asset.ticker.endswith(".SA") else f"{asset.ticker}.SA"
        
        try:
            y_ticker = yf.Ticker(ticker_symbol)
            info = y_ticker.info
            
            def get_val(key: str, fmt: str = "{:.2f}") -> str:
                value = info.get(key)
                if value is None:
                    return "N/A"
                try:
                    return fmt.format(value)
                except (ValueError, TypeError):
                    return str(value)

            data = {
                "Price": get_val("currentPrice", "R$ {:.2f}"),
                "P/VP (Price to Book)": get_val("priceToBook")
            }

            if isinstance(asset, EquityAsset):
                data["P/L (Trailing P/E)"] = get_val("trailingPE")
            
            elif isinstance(asset, REITAsset):
                pass

            return data

        except Exception as e:
            logger.error(f"Failed to fetch yfinance data for {asset.ticker}: {e}")
            return {"Error": "Financial data unavailable"}