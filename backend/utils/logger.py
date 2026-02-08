import logging
import os
import sys
from typing import Optional

# ANSI escape sequences for coloring
RESET = "\033[0m"
COLOR_LEVELS = {
    "DEBUG": "\033[36m",     # Cyan
    "INFO": "\033[32m",      # Green
    "WARNING": "\033[33m",   # Yellow
    "ERROR": "\033[31m",     # Red
    "CRITICAL": "\033[41m\033[97m",  # Bright White on Red background
}
COLOR_TIME = "\033[90m"      # Light gray for timestamp
COLOR_NAME = "\033[35m"      # Magenta for logger name
COLOR_MESSAGE = "\033[37m"   # White for message

LOG_LEVEL = os.getenv("BACKEND_LOG_LEVEL", "INFO").upper()

class ColoredFormatter(logging.Formatter):
    def format(self, record):
        asctime = self.formatTime(record, self.datefmt)
        levelname = record.levelname
        name = record.name

        color_level = COLOR_LEVELS.get(levelname, "")
        colored_level = f"{color_level}{levelname:<8}{RESET}"
        colored_time = f"{COLOR_TIME}{asctime}{RESET}"
        colored_name = f"{COLOR_NAME}{name}{RESET}"
        colored_msg = f"{COLOR_MESSAGE}{record.getMessage()}{RESET}"

        log = f"{colored_time} | {colored_level} | {colored_name} | {colored_msg}"
        if record.exc_info:
            log += f"\n{self.formatException(record.exc_info)}"
        return log

# Remove all existing handlers associated with the root logger.
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(getattr(logging, LOG_LEVEL, logging.DEBUG))
handler.setFormatter(ColoredFormatter())

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.DEBUG),
    handlers=[handler],
)

def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Central logger factory for the backend.

    - Uses a consistent color format and log level across modules.
    - Call `get_logger(__name__)` at module level to get a logger.
    """
    return logging.getLogger(name if name is not None else "backend")

