import logging
from threading import Thread
from time import sleep, time

from dotenv import load_dotenv

from pot.network.blockchain import PoT
from pot.network.node import Node
from pot.network.request import Request
from pot.utils import setup_logger


print(f"Starting {__file__}")

"""
Loading env values
"""
load_dotenv()

"""
Configuring logger
"""
setup_logger("BLOCK")

sleep(0.1)

pot = PoT()
pot.load(only_from_file=True)

node = pot.nodes.find_by_identifier(pot.self_node.identifier)

while True:
    
    if not pot.nodes.is_validator(node):
        sleep(5)
        continue

    print("Checking")
    if pot.blockchain.get_last_block().timestamp + 100 < int(time()) and pot.blockchain.txs_verified.all():
        block = pot.blockchain.create_block(pot.self_node)

        def send(node: Node):
            Request.send_blockchain_new_block(node.host, node.port, block.encode())

        threads = []
        for node in pot.nodes.all():
            if node.identifier == pot.self_node.identifier:
                continue
            logging.info(f"Sending new node to host: {node.host}:{node.port} - starting thread")
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

    sleep(5)


