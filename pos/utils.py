import logging
import os
from logging.handlers import TimedRotatingFileHandler


def setup_logger() -> None:
    handler = TimedRotatingFileHandler(os.path.join(os.getenv('LOG_DIR', "log"), "app.log"), when="midnight")
    handler.suffix = "%Y%m%d"
    level = logging.getLevelName(os.getenv('LOG_LEVEL', 'INFO'))
    logging.basicConfig(
        format="%(asctime)s %(message)s",
        level=level,
        handlers=[handler],
        encoding="UTF-8",
    )