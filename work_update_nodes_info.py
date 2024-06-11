import os
import socket
from time import sleep

from dotenv import load_dotenv

from pot.network.blockchain import PoT
from pot.utils import setup_logger


print(f"Starting {__file__}")

"""
Loading env values
"""
load_dotenv()

"""
Configuring logger
"""
setup_logger("UPDATE")

sleep(0.1)

pot = PoT()
pot.load(only_from_file=True)

hostname = socket.gethostname()
ip = socket.gethostbyname(hostname)

genesis_hostname = os.getenv("GENESIS_NODE")
genesis_ip = socket.gethostbyname(genesis_hostname)
if ip == genesis_ip:
    exit()

sleep(30.0)

pot.update_from_validator_node(genesis_ip)
