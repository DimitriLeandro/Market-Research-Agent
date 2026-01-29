import yaml
import json
import os
from pathlib import Path
from typing import List, Dict, Any

class Config:
    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    CREDENTIALS_PATH = BASE_DIR / "credentials" / "credentials.json"
    PORTFOLIO_PATH = BASE_DIR / "market_agent" / "config" / "portfolio.yaml"
    RESULTS_DIR = BASE_DIR / "results"
    LOGS_DIR = BASE_DIR / "logs"
    PROMPTS_DIR = BASE_DIR / "market_agent" / "prompts" / "files"

    @classmethod
    def load_api_key(cls) -> str:
        if not cls.CREDENTIALS_PATH.exists():
            raise FileNotFoundError(f"Credentials not found at {cls.CREDENTIALS_PATH}")
        with cls.CREDENTIALS_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
            return data["gemini_api_key"]

    @classmethod
    def load_portfolio(cls) -> List[Dict[str, Any]]:
        with cls.PORTFOLIO_PATH.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return data.get("assets", [])