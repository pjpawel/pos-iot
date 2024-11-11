import logging
import os
import sys
from logging.handlers import TimedRotatingFileHandler


def setup_logger(prefix: str = "", level_str: str | None = None) -> None:
    handler = TimedRotatingFileHandler(
        os.path.join(os.getenv("LOG_DIR", "log"), "app.log"), when="midnight"
    )
    handler.suffix = "%Y%m%d"
    name = sys.argv[0].replace("work_", "").replace("start_", "").replace(".py", "")
    f_handler = logging.FileHandler(
        os.path.join(os.getenv("LOG_DIR", "log"), f"app-{name}.log")
    )
    if level_str is None:
        level_str = os.getenv("LOG_LEVEL", "INFO")
    level = logging.getLevelName(level_str)
    logging.basicConfig(
        format=f"%(asctime)s  %(process)d/{prefix}  %(module)s.%(lineno)d  %(levelname)s: %(message)s",
        level=level,
        handlers=[handler, f_handler],  # f_handler
        encoding="UTF-8",
    )
