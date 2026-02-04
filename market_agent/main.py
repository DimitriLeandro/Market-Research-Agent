import asyncio
import logging
import sys
import argparse
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from market_agent.config.logging_config import setup_logging
from market_agent.config.settings import Config
from market_agent.agent import MarketAgent

def parse_arguments():
    parser = argparse.ArgumentParser(description="AI Market Research Agent")
    parser.add_argument(
        "--test", 
        action="store_true", 
        help="Run in TEST MODE using a smaller portfolio subset (portfolio_test.yaml)."
    )
    return parser.parse_args()

def main():
    args = parse_arguments()
    
    setup_logging(Config.LOGS_DIR)
    logger = logging.getLogger("main")
    
    mode_label = "TEST MODE" if args.test else "PRODUCTION MODE"
    logger.info(f"Initializing Market Agent in {mode_label}...")
    
    try:
        # Pass the test flag to the agent
        agent = MarketAgent(test_mode=args.test)
        asyncio.run(agent.run_cycle())
        logger.info("Cycle completed successfully.")
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()