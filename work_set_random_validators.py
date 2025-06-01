import logging
import os
import socket
import random
from time import sleep, time

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
setup_logger("SET_RANDOM_VALIDATORS")

sleep(0.1)

hostname = socket.gethostname()
ip = socket.gethostbyname(hostname)

genesis_hostname = os.getenv("GENESIS_NODE")
genesis_ip = socket.gethostbyname(genesis_hostname)
if ip != genesis_ip:
    exit()

pot = PoST()
pot.load(only_from_file=True)

start = time()
last_nodes_len = 1
while True:
    nodes_len = len(pot.nodes.all())
    if nodes_len == last_nodes_len:
        if time() - start > 10.0:
            break
    else:
        last_nodes_len = nodes_len
        start = time()
    sleep(3)

sleep(15.0)
logging.debug("Starting setting new validators")
validators_number = pot.nodes.calculate_validators_number()

identifiers = []
for node in pot.nodes.all():
    identifiers.append(node.identifier)

validator_ids = random.sample(identifiers, validators_number)

pot.nodes.validators.set_validators(validator_ids)
logging.info(f"Validators list updated: {[idnt.hex for idnt in validator_ids]}")
pot.send_validators_list()
logging.debug(f"Validators list sent to all nodes")
