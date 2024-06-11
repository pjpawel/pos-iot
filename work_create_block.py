from time import sleep, time

from dotenv import load_dotenv

from pot.network.blockchain import PoT
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

    if pot.blockchain.get_last_block().timestamp + 60 < int(time()) and pot.blockchain.txs_verified.all():
        block = pot.blockchain.create_block(pot.self_node)
        for node in pot.nodes.all():
            if node.identifier == pot.self_node.identifier:
                continue
            Request.send_blockchain_new_block(node.host, node.port, block.encode())

    sleep(5)
    continue


