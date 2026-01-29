import asyncio
import logging
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from market_agent.config.logging_config import setup_logging
from market_agent.config.settings import Config
from market_agent.agent import MarketAgent

def main():
    setup_logging(Config.LOGS_DIR)
    logger = logging.getLogger("main")
    
    logger.info("Initializing Market Agent (Async/Pydantic/Jinja2)...")
    
    try:
        agent = MarketAgent()
        asyncio.run(agent.run_cycle())
        logger.info("Daily cycle completed.")
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()