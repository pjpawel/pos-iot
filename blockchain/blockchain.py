import os
import json

from .block import Block
from network.peer import Handler
from .util import is_file, is_dir


class Node:
    host: str
    port: int


class Blockchain:
    BLOCKCHAIN_PATH = 'blockchain.json'
    NODES_PATH = 'nodes.json'


    storage_dir: str
    chain: list[Block]
    nodes: list

    def __init__(self):
        self.storage_dir = os.getenv('STORAGE_DIR')
        self.chain = []

    def add_block(self, block: Block) -> None:
        self.chain.append(block)

    def has_storage_files(self) -> bool:
        return is_dir(self.storage_dir) \
               and is_file(os.path.join(self.storage_dir, self.BLOCKCHAIN_PATH)) \
               and is_file(os.path.join(self.storage_dir, self.NODES_PATH))

    def load_from_storage(self) -> None:
        with open(os.path.join(self.storage_dir, self.BLOCKCHAIN_PATH)) as f:
            self.chain = json.load(f)
        with open(os.path.join(self.storage_dir, self.NODES_PATH)) as f:
            self.nodes = json.load(f)

    def dump_to_storage(self) -> None:
        with open(os.path.join(self.storage_dir, self.BLOCKCHAIN_PATH), 'w') as f:
            json.dump(self.chain, f)
        with open(os.path.join(self.storage_dir, self.NODES_PATH), 'w') as f:
            json.dump(self.nodes, f)

    def load_from_genesis_node(self, genesis_ip: str) -> None:
        # Call genesis node
        pass


class BlockchainHandler(Handler):

    def handle(self, data: str):
        print("=========")
        print("Data received")
        print(data)
        print("=========")
