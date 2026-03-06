from pathlib import Path
from datetime import datetime
import logging


def setup_logger():

    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")

    log_file = log_dir / f"ciec_{timestamp}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
        ]
    )

    logging.info("=== CIEC iniciado ===")

    return log_file