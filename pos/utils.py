import logging
import os
from logging.handlers import TimedRotatingFileHandler


def setup_logger() -> None:
    handler = TimedRotatingFileHandler(os.path.join(os.getenv('LOG_DIR', "log"), "app.log"), when="midnight")
    handler.suffix = "%Y%m%d"
    level = logging.getLevelName(os.getenv('LOG_LEVEL', 'INFO'))
    logging.basicConfig(
        format="%(asctime)s %(created)f %(levelname)s :::%(filename)s.%(module)s.%(lineno)d: %(message)s",
        level=level,
        handlers=[handler],
        encoding="UTF-8",
    )
