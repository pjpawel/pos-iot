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
    os.environ["POST_SCENARIOS"] = "INSTANT_SENDER"
    os.environ["VALIDATORS_PART"] = "0.2"

    if os.environ.get("SIMULATION") is None:
        raise Exception("SIMULATION env variable is not set")
    match int(os.environ["SIMULATION"]):
        case 2:
            os.environ["MAX_DELAY"] = "300"
        case 3:
            if randint(0, 100) % 4 == 0:
                os.environ["POST_SCENARIOS"] = "MAD_SENDER"
        case 4:
            # 50%
            if randint(0, 100) % 2 == 0:
                os.environ["POST_SCENARIOS"] = "MAD_SENDER"
        case 5:
            # 75%
            if randint(0, 100) % 4 != 0:
                os.environ["POST_SCENARIOS"] = "MAD_SENDER"
        case 6:
            os.environ["POST_SCENARIOS"] = "MAD_SENDER"
        case 7:
            os.environ["MAX_DELAY"] = "50"
        case 8:
            os.environ["MAX_DELAY"] = "100"
            os.environ["MIN_DELAY"] = "50"
        case 9:
            os.environ["MAX_DELAY"] = "150"
            os.environ["MIN_DELAY"] = "100"
        case 10:
            os.environ["MAX_DELAY"] = "200"
            os.environ["MIN_DELAY"] = "150"
        case 11:
            os.environ["MAX_DELAY"] = "250"
            os.environ["MIN_DELAY"] = "200"
        case 12:
            os.environ["VALIDATORS_PART"] = "0.1"
        case 13:
            os.environ["VALIDATORS_PART"] = "0.3"
        case 14:
            os.environ["VALIDATORS_PART"] = "0.4"
        case 15:
            os.environ["VALIDATORS_PART"] = "0.5"
        case 16:
            os.environ["VALIDATORS_PART"] = "0.6"
        case 17:
            os.environ["VALIDATORS_PART"] = "0.7"
        case 18:
            os.environ["VALIDATORS_PART"] = "0.8"
        case 19:
            os.environ["VALIDATORS_PART"] = "0.9"
        case 20:
            os.environ["VALIDATORS_PART"] = "0.25"
        case 21:
            os.environ["VALIDATORS_PART"] = "0.35"
        case 22:
            os.environ["VALIDATORS_PART"] = "0.45"
        case 23:
            os.environ["VALIDATORS_PART"] = "0.55"
        # case _:
        #     os.environ["POST_SCENARIOS"] = "INSTANT_SENDER"
        #     os.environ["VALIDATORS_PART"] = "0.2"
