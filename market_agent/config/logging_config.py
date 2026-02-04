import logging
import sys
from pathlib import Path
from datetime import datetime

def setup_logging(log_dir: Path):
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate timestamped filename for per-execution logging
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_filename = f"{timestamp}.log"
    log_file = log_dir / log_filename

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8', mode='w'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Suppress noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    
    # Log the startup to verify correct file creation
    logging.info(f"Logging initialized. Writing to: {log_file}")