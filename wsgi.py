import os
import socket

from dotenv import load_dotenv

from pos.blockchain.blockchain import PoS
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

    """
    Load blockchain
    """
    hostname = socket.gethostname()
    ip = socket.gethostbyname(hostname)
    genesis_ip = os.getenv("GENESIS_NODE")

    pos = PoS()
    pos.load()

    blockchain = pos.blockchain
    self_node = pos.self_node

    return app
