from dotenv import load_dotenv

from pos.start_node_flask import app
from pos.utils import setup_logger


def main():
    """
    Loading env values
    """
    load_dotenv()

    """
    Configuring logger
    """
    setup_logger()

    return app
