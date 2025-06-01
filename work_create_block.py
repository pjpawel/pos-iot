import logging
from threading import Thread
from time import sleep, time

from dotenv import load_dotenv

from post.network.blockchain import PoST
from post.network.node import Node
from post.network.request import Request
from post.network.trust import TrustChangeType
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
setup_logger("BLOCK", "DEBUG")

sleep(0.1)

pot = PoST()
pot.load(only_from_file=True)

self_node = pot.nodes.find_by_identifier(pot.self_node.identifier)

while True:

    if not pot.nodes.is_validator(self_node):
        sleep(10)
        continue

    logging.debug("Checking block should be created")

    if (
        pot.blockchain.get_last_block().timestamp + 150 < int(time())
        and pot.blockchain.txs_verified.all()
    ):
        block = pot.blockchain.create_block(pot.self_node)

        def send(node: Node):
            Request.send_blockchain_new_block(node.host, node.port, block.encode())

        threads = []
        for node in pot.nodes.all():
            if node.identifier == self_node.identifier:
                continue
            logging.debug(
                f"Sending new block to host: {node.host}:{node.port} - starting thread"
            )
            th = Thread(target=send, args=[node])
            th.start()
            threads.append(th)

        # Wait for all to end
        while True:
            if len(threads) != 0:
                break
            for thread in threads:
                if not thread.is_alive():
                    threads.remove(thread)

        pot.change_node_trust(
            self_node,
            TrustChangeType.BLOCK_CREATED,
            additional_data=block.signature.hex(),
        )

    sleep(10)
