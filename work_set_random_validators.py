import logging
import os
import socket
import random
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
setup_logger("SET_RANDOM_VALIDATORS")

sleep(0.1)

hostname = socket.gethostname()
ip = socket.gethostbyname(hostname)

genesis_hostname = os.getenv("GENESIS_NODE")
genesis_ip = socket.gethostbyname(genesis_hostname)
if ip != genesis_ip:
    exit()

pot = PoT()
pot.load(only_from_file=True)

sleep(70.0)
logging.info("Starting setting new validators")
validators_number = pot.nodes.calculate_validators_number()

identifiers = []
for node in pot.nodes.all():
    identifiers.append(node.identifier)

validator_ids = random.sample(identifiers, validators_number)

pot.nodes.validators.set_validators(validator_ids)
logging.info(f"Validators list updated: {[idnt.hex for idnt in validator_ids]}")
pot.send_validators_list()
logging.info(f"Validators list sent to all nodes")
