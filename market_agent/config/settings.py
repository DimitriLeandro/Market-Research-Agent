import yaml
import json
import os
from pathlib import Path
from typing import List, Dict, Any

class Config:
    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    CREDENTIALS_PATH = BASE_DIR / "credentials" / "credentials.json"
    
    # Paths for both Production and Test portfolios
    PORTFOLIO_PATH = BASE_DIR / "market_agent" / "config" / "portfolio.yaml"
    TEST_PORTFOLIO_PATH = BASE_DIR / "market_agent" / "config" / "portfolio_test.yaml"
    
    RESULTS_DIR = BASE_DIR / "results"
    LOGS_DIR = BASE_DIR / "logs"
    PROMPTS_DIR = BASE_DIR / "market_agent" / "prompts"

    @classmethod
    def load_api_key(cls) -> str:
        if not cls.CREDENTIALS_PATH.exists():
            raise FileNotFoundError(f"Credentials not found at {cls.CREDENTIALS_PATH}")
        with cls.CREDENTIALS_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
            return data["gemini_api_key"]

    @classmethod
    def load_portfolio(cls, test_mode: bool = False) -> List[Dict[str, Any]]:
        """
        Loads the portfolio assets. 
        If test_mode is True, loads from portfolio_test.yaml.
        Otherwise, loads from the standard portfolio.yaml.
        """
        target_path = cls.TEST_PORTFOLIO_PATH if test_mode else cls.PORTFOLIO_PATH
        
        if not target_path.exists():
             raise FileNotFoundError(f"Portfolio configuration not found at {target_path}")

        with target_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return data.get("assets", [])