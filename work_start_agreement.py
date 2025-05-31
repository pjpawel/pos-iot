import logging
import socket
from threading import Thread
from time import sleep, time
from math import ceil
from random import randint
from uuid import UUID

from dotenv import load_dotenv

from post.network.blockchain import PoT
from post.network.node import Node
from post.network.request import Request
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
setup_logger("START_AGREEMENT", "DEBUG")

sleep(70)

pot = PoT()
pot.load(only_from_file=True)

node = pot.self_node.get_node()

logging.info(
    f"Node: {node.identifier}. Socket: {socket.gethostbyname(socket.gethostname())}"
)

while True:

    if not pot.nodes.is_validator(node):
        sleep(50)
        continue

    logging.info(
        f"Checking if validator should be starting. This node is {node.identifier.hex}"
    )
    agreement_info = pot.nodes.validator_agreement_info
    agreement_info.refresh()
    if (
        not agreement_info.is_started
        and len(pot.nodes.validator_agreement_result.all()) == 0
        and agreement_info.last_successful_agreement < time() - 139
    ):
        logging.info("Starting agreement")
        # Prepare nodes list
        nodes = pot.nodes.prepare_all_nodes_info()
        nodes = sorted(nodes, key=lambda node_info: node_info["trust"])
        validator_len = max(2, ceil(len(nodes) * 0.1))

        half_validator_len = int(validator_len / 2)
        agreement_list = nodes[0:half_validator_len]

        while True:
            if validator_len == len(agreement_list):
                break
            index = randint(half_validator_len, validator_len)
            if nodes[index] not in agreement_list:
                agreement_list.append(nodes[index])

        validator_list = [node["identifier"] for node in agreement_list]
        logging.info(f"Proposed validator list: " + ", ".join(validator_list))

        # Send list
        node_id_data = {"list": validator_list}

        def send(func):
            threads = []
            for node in pot.nodes.all():
                if (
                    node.identifier == pot.self_node.identifier
                    or node.identifier not in pot.nodes.validators.all()
                ):
                    continue
                logging.info(
                    f"Sending new validator agreement to host: {node.host}:{node.port} - starting thread"
                )
                th = Thread(target=func, args=[node])
                th.start()
                threads.append(th)

            # Wait for all to end
            while True:
                if len(threads) != 0:
                    break
                for thread in threads:
                    if not thread.is_alive():
                        threads.remove(thread)

        def action(node: Node):
            Request.send_validator_agreement_start(node.host, node.port, node_id_data)

        pot.nodes.validator_agreement_info.set_info_data(True, [node.identifier])
        pot.nodes.set_agreement_list([UUID(validator) for validator in validator_list])
        pot.nodes.validator_agreement_result.add(node.identifier, True)
        send(action)

    sleep(30)
