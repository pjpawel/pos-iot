import os
import json
from hashlib import sha256
from time import time

import requests

from .block import Block, BlockCandidate
from pos.network.peer import Handler
from .transaction import Tx
from .utils import is_file, is_dir
from .node import Node, SelfNode


class Blockchain:
    BLOCKCHAIN_PATH = 'blockchain.json'
    NODES_PATH = 'nodes.json'

    storage_dir: str
    chain: list[Block]
    nodes: list[Node]
    candidate: BlockCandidate | None = None

    def __init__(self):
        self.storage_dir = os.getenv('STORAGE_DIR')
        self.chain = []
        self.nodes = []

    def add_new_transaction(self, tx: Tx):
        if not self.candidate:
            self.candidate = BlockCandidate.create_new([])
        tx.validate(self.nodes)
        self.candidate.transactions.append(tx)

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

    def create_first_block(self, self_node: SelfNode) -> None:
        block = BlockCandidate.create_new([])
        self.chain.append(block.sign(
            sha256(b'0000000000').digest(),
            self_node.identifier,
            self_node.private_key
        ))

    def load_from_genesis_node(self, genesis_ip: str) -> None:
        data = {
            "port": 5000,
            "register": True,
            "lastBlock": None
        }
        response = requests.post(f"http://{genesis_ip}:{5000}/genesis/register_node", json=data)
        if response.status_code != 200:
            raise Exception(f"Cannot register node in genesis node: {genesis_ip}:{5000}")
        response_json = response.json()
        self.chain = [block.__dict__ for block in response_json["blockchain"]]
        self.nodes = [node.__dict__ for node in response_json["nodes"]]

    def update_from_genesis_node(self, genesis_ip: str) -> None:
        data = {"port": 5000}
        response = requests.post(f"http://{genesis_ip}:{5000}/genesis/register_node", json=data)
        if response.status_code != 200:
            raise Exception(f"Cannot register node in genesis node: {genesis_ip}:{5000}")
        response_json = response.json()
        self.chain = [Block.decode() for block in response_json["blockchain"]]
        self.nodes = [node for node in response_json["nodes"]]

    def exclude_self_node(self, self_ip: str):
        for node in self.nodes:
            if node.host == self_ip:
                self.nodes.remove(node)

    def blocks_to_dict(self):
        return [block.__dict__ for block in self.chain]

    def nodes_to_dict(self):
        return [node.__dict__ for node in self.nodes]

    # def __del__(self):
    #     self.dump_to_storage()


class BlockchainHandler(Handler):
    blockchain: Blockchain

    def __init__(self, blockchain):
        self.blockchain = blockchain

    def handle(self, data: str):
        print("=========")
        print("Data received")
        print(data)
        print("=========")


class PoS:
    blockchain: Blockchain

