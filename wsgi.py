from dotenv import load_dotenv

from pot.start_node_flask import app
from pot.utils import setup_logger


def main():
    """
    Loading env values
    """
    # load_dotenv()
    #
    # """
    # Configuring logger
    # """
    # setup_logger()

    return app
