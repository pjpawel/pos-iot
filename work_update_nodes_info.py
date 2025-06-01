import os
import socket
from time import sleep

from dotenv import load_dotenv

from post.network.blockchain import PoST
from post.utils import setup_logger, prepare_simulation_env


print(f"Starting {__file__}")

"""
Loading env values
"""
load_dotenv()
prepare_simulation_env()

"""
Configuring logger
"""
setup_logger("UPDATE")

sleep(0.1)

pot = PoST()
pot.load(only_from_file=True)

hostname = socket.gethostname()
ip = socket.gethostbyname(hostname)

genesis_hostname = os.getenv("GENESIS_NODE")
genesis_ip = socket.gethostbyname(genesis_hostname)
if ip == genesis_ip:
    exit()

sleep(30.0)

pot.update_from_validator_node(genesis_ip)
