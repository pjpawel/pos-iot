import logging
import os
import sys
from random import randint
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


def prepare_simulation_env():
    if os.environ.get("SIMULATION") is None:
        raise Exception("SIMULATION env variable is not set")
    match int(os.environ["SIMULATION"]):
        case 2:
            os.environ["MAX_DELAY"] = "300"
        case 3:
            if randint(0, 100) % 4 == 0:
                os.environ["POT_SCENARIOS"] = "mad_sender"
        case _:
            os.environ["POT_SCENARIOS"] = "instant_sender"
