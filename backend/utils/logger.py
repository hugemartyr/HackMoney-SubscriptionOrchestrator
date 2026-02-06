import logging
import os
from typing import Optional


LOG_LEVEL = os.getenv("BACKEND_LOG_LEVEL", "INFO").upper()
LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"

# Configure root logger once for the entire backend.
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.DEBUG),
    format=LOG_FORMAT,
)


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Central logger factory for the backend.

    - Uses a consistent format and log level across modules.
    - Call `get_logger(__name__)` at module level to get a logger.
    """
    return logging.getLogger(name if name is not None else "backend")

