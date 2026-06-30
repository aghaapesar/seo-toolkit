"""Logging configuration for Seo Toolkit."""

import logging
import sys
from pathlib import Path


LOG_FILE = "logs/seo_toolkit.log"


def configure_logging(verbose: bool = False) -> logging.Logger:
    """
    Configure application logging to file and stdout.

    Input:
        verbose: Enable DEBUG level when True.

    Output:
        Root application logger.
    """
    Path("logs").mkdir(exist_ok=True)

    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler(sys.stdout),
        ],
    )
    return logging.getLogger("seo_toolkit")
